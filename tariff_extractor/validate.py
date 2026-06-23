import json
from pathlib import Path
from datetime import datetime, date, timezone
from jsonschema import validate as json_validate, ValidationError

SCHEMA_DIR = Path(__file__).parent / "schema"

KNOWN_UNITS = {"gal", "kgal", "ccf", "hcf", "cf", "m3"}

# hcf is a synonym for ccf (same physical quantity, different label)
UNIT_SYNONYMS = {"hcf": "ccf"}

# Plausible price-per-unit ranges for US residential water
PRICE_RANGES = {
    "gal":  (0.0010, 0.0250),
    "kgal": (1.00,   25.00),
    "ccf":  (0.75,   25.00),
    "hcf":  (0.75,   25.00),
    "cf":   (0.0075, 0.2500),
    "m3":   (0.26,   6.60),
}


def validate(tariff: dict, bill: float | None = None, state_stats: dict | None = None) -> dict:
    """Run hard checks then scored checklist on an extracted tariff.

    Args:
        tariff: extracted tariff dict
        bill: computed 6k-gal monthly bill (from bill.compute_bill), used for bill_sanity check
        state_stats: dict with {q1, q3, iqr, n} for state plausibility check, or None to skip

    Returns dict with:
        hard_passed (bool), hard_checks (dict), score (float),
        checks (dict of check_name → bool|None), checks_passed (int),
        checks_total (int), confidence (str), state_peers_n (int|None)
    """
    unit = tariff.get("unit")
    vol = tariff.get("volumetric") or {}
    tiers = vol.get("tiers") or []

    # ── Hard checks ──────────────────────────────────────────────────────────
    hard_checks = {
        "known_unit": unit in KNOWN_UNITS,
        "tier_boundaries_ok": _check_tier_boundaries(tiers),
    }
    if bill is not None:
        hard_checks["bill_sanity"] = 10.0 <= bill <= 300.0
    hard_passed = all(hard_checks.values())

    if not hard_passed:
        failed = [k for k, v in hard_checks.items() if not v]
        return {
            "hard_passed": False,
            "hard_checks": hard_checks,
            "score": 0.0,
            "checks": {},
            "checks_passed": 0,
            "checks_total": 0,
            "confidence": "flagged",
            "confidence_reasons": [f"hard check failed: {', '.join(failed)}"],
            "state_peers_n": None,
        }

    normalized_unit = UNIT_SYNONYMS.get(unit, unit)

    # ── Scored checklist ─────────────────────────────────────────────────────
    checks: dict[str, bool | None] = {}

    # 1. Monotonic pricing (non-decreasing per-unit prices within each season)
    checks["monotonic_pricing"] = _check_monotonic(tiers)

    # 2. Price range plausible
    checks["price_range_plausible"] = _check_price_range(tiers, normalized_unit)

    # 3. Fixed charge range ($0–$150/month equivalent)
    fixed = tariff.get("fixed_charge")
    checks["fixed_charge_range"] = fixed is None or (0 <= fixed <= 150)

    # 4. No zero tier prices
    prices = [t["price"] for t in tiers if t.get("price") is not None]
    checks["no_zero_prices"] = len(prices) == 0 or all(p > 0 for p in prices)

    # 5. Tier count sane (1–8)
    checks["tier_count_sane"] = len(tiers) == 0 or (1 <= len(tiers) <= 8)

    # 5b. Tier boundary scale consistent with unit
    # Catches gallon/kgal confusion: boundaries of 6000 with unit=kgal = 6M gal (impossible residential)
    checks["boundary_scale_ok"] = _check_boundary_scale(tiers, normalized_unit)

    # 6. Customer class residential
    cc = (tariff.get("customer_class") or "").lower()
    checks["customer_class_residential"] = "residential" in cc

    # 8. Effective date parseable (if present, must be a real date not >1yr in future)
    checks["effective_date_ok"] = _check_effective_date(tariff)

    # 9. State plausibility — conditional on ≥10 peers and a computed bill
    state_peers_n = state_stats.get("n") if state_stats else None
    if state_stats and (state_stats.get("n") or 0) >= 10 and bill is not None:
        q1, q3, iqr = state_stats["q1"], state_stats["q3"], state_stats["iqr"]
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        checks["state_plausible"] = lower <= bill <= upper
    else:
        checks["state_plausible"] = None  # skip — not enough state peers

    # ── Score ─────────────────────────────────────────────────────────────────
    active = {k: v for k, v in checks.items() if v is not None}
    passed = sum(1 for v in active.values() if v)
    total = len(active)
    score = round(passed / total, 3) if total else 0.0

    confidence = "model_estimate" if score >= 0.80 else "flagged"
    reasons = [f"{k}: {'pass' if v else 'FAIL'}" for k, v in active.items() if not v]

    return {
        "hard_passed": True,
        "hard_checks": hard_checks,
        "score": score,
        "checks": checks,
        "checks_passed": passed,
        "checks_total": total,
        "confidence": confidence,
        "confidence_reasons": reasons if reasons else ["all checks passed"],
        "state_peers_n": state_peers_n,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _check_tier_boundaries(tiers: list[dict]) -> bool:
    """Verify tier boundaries are gapless and contiguous within each season."""
    if not tiers:
        return True

    # Group by season (None = no season field)
    seasons: dict[str, list[dict]] = {}
    for t in tiers:
        s = t.get("season") or "_default"
        seasons.setdefault(s, []).append(t)

    for season_tiers in seasons.values():
        sorted_tiers = sorted(season_tiers, key=lambda t: t.get("from") or 0)

        if sorted_tiers[0].get("from") != 0:
            return False

        for i in range(len(sorted_tiers) - 1):
            curr_to = sorted_tiers[i].get("to")
            next_from = sorted_tiers[i + 1].get("from")
            if curr_to is None or curr_to != next_from:
                return False

        if len(sorted_tiers) > 1 and sorted_tiers[-1].get("to") is not None:
            return False

    return True


def _check_monotonic(tiers: list[dict]) -> bool:
    """Prices should be non-decreasing within each season (conservation pricing)."""
    if not tiers:
        return True

    seasons: dict[str, list[dict]] = {}
    for t in tiers:
        s = t.get("season") or "_default"
        seasons.setdefault(s, []).append(t)

    for season_tiers in seasons.values():
        sorted_tiers = sorted(season_tiers, key=lambda t: t.get("from") or 0)
        prices = [t["price"] for t in sorted_tiers if t.get("price") is not None and t["price"] > 0]
        if len(prices) > 1 and prices != sorted(prices):
            return False  # declining block — flag but don't hard-reject

    return True


def _check_price_range(tiers: list[dict], unit: str) -> bool:
    """All tier prices must fall within the plausible range for the given unit."""
    bounds = PRICE_RANGES.get(unit)
    if not bounds:
        return True  # unknown unit already caught by hard check
    lo, hi = bounds
    prices = [t["price"] for t in tiers if t.get("price") is not None]
    if not prices:
        return True
    return all(lo <= p <= hi for p in prices)


def _check_boundary_scale(tiers: list[dict], unit: str) -> bool:
    """Catches gallon/kgal unit confusion: e.g. boundaries of 6,000 with unit=kgal is 6M gallons."""
    max_plausible = {
        "gal":  1_000_000,
        "kgal": 1_000,
        "ccf":  1_340,
        "hcf":  1_340,
        "cf":   133_000,
        "m3":   3_785,
    }.get(unit)
    if not max_plausible or not tiers:
        return True
    non_null = [t["to"] for t in tiers if t.get("to") is not None]
    return not non_null or max(non_null) <= max_plausible


def _check_effective_date(tariff: dict) -> bool:
    """If effective_date is present it must parse and not be >1yr in the future."""
    ed = tariff.get("effective_date")
    if not ed:
        return True
    try:
        dt = datetime.strptime(str(ed), "%Y-%m-%d").date()
        today = date.today()
        return dt <= date(today.year + 1, today.month, today.day)
    except (ValueError, TypeError):
        return False
