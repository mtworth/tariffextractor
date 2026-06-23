UNIT_LABELS = {"ccf": "CCF", "kgal": "kgal", "gal": "gal"}
PERIOD_LABELS = {"monthly": "monthly", "bimonthly": "bimonthly", "quarterly": "quarterly"}

UNIT_CONVERSIONS = {
    "ccf": lambda gal: gal / 748.0,
    "kgal": lambda gal: gal / 1000.0,
    "gal": lambda gal: gal,
}

# How many months each billing period covers
PERIOD_MONTHS = {"monthly": 1, "bimonthly": 2, "quarterly": 3}


def compute_bill(tariff: dict, volume_gal: float = 6000.0) -> tuple[float, dict | None]:
    """Return (monthly_bill, seasonal_breakdown_or_None) at volume_gal per month.

    Tier boundaries and fixed charges are expressed in the source's billing period.
    We scale volume by the period length, compute the full-period bill, then divide
    back to a monthly equivalent so all utilities are comparable on the same basis.
    """
    unit = tariff.get("unit", "ccf")
    fixed = tariff.get("fixed_charge") or 0.0
    convert = UNIT_CONVERSIONS.get(unit, UNIT_CONVERSIONS["ccf"])

    period = PERIOD_MONTHS.get(tariff.get("bill_frequency") or "monthly", 1)
    # Volume for one full billing period
    volume = convert(volume_gal * period)

    vol = tariff.get("volumetric", {})
    tiers = vol.get("tiers") or []

    if vol.get("type") == "seasonal_flat":
        # Prefer explicit seasonal dict; fall back to season-tagged tiers (one flat tier per season)
        seasonal = vol.get("seasonal") or {}
        if not seasonal:
            for t in tiers:
                s = t.get("season") or "default"
                if s not in seasonal and t.get("price") is not None:
                    seasonal[s] = t["price"]
        breakdown = {
            s: round((fixed + volume * p) / period, 2)
            for s, p in seasonal.items() if p is not None
        }
        if breakdown:
            return max(breakdown.values()), breakdown
        return round(fixed / period, 2), None

    vol_charge = 0.0
    remaining = volume

    for t in tiers:
        if remaining <= 0:
            break
        to_qty = t.get("to")
        if to_qty is not None:
            used = min(remaining, to_qty - t.get("from", 0))
        else:
            used = remaining
        vol_charge += used * t["price"]
        remaining -= used

    return round((fixed + vol_charge) / period, 2), None


def bill_explanation(tariff: dict, volume_gal: float = 6000.0) -> list[str]:
    """Return step-by-step bill calculation as a list of human-readable lines."""
    unit = tariff.get("unit", "ccf")
    fixed = tariff.get("fixed_charge") or 0.0
    convert = UNIT_CONVERSIONS.get(unit, UNIT_CONVERSIONS["ccf"])
    period = PERIOD_MONTHS.get(tariff.get("bill_frequency") or "monthly", 1)
    ul = UNIT_LABELS.get(unit, unit)
    pl = PERIOD_LABELS.get(tariff.get("bill_frequency") or "monthly", "monthly")

    lines = []

    # Fixed charge
    if fixed:
        if period > 1:
            lines.append(f"Fixed: ${fixed:.2f} {pl} ÷ {period} = ${fixed/period:.2f}/mo")
        else:
            lines.append(f"Fixed: ${fixed:.2f}/mo")

    # Volume
    period_vol = volume_gal * period
    converted = convert(period_vol)
    if period > 1:
        lines.append(f"Volume: {volume_gal:,.0f} gal × {period} = {period_vol:,.0f} gal = {converted:.2f} {ul}")
    else:
        lines.append(f"Volume: {volume_gal:,.0f} gal = {converted:.2f} {ul}")

    vol = tariff.get("volumetric", {})
    tiers = vol.get("tiers") or []

    # Seasonal flat
    if vol.get("type") == "seasonal_flat":
        seasonal = vol.get("seasonal") or {}
        if not seasonal:
            for t in tiers:
                s = t.get("season") or "default"
                if s not in seasonal and t.get("price") is not None:
                    seasonal[s] = t["price"]
        for season, rate in seasonal.items():
            if rate is not None:
                charge = converted * rate
                total = (fixed + charge) / period
                lines.append(f"  {season.title()}: {converted:.2f} {ul} × ${rate:.4f} = ${charge:.2f} → ${total:.2f}/mo")
        return lines

    # Tiered / flat
    remaining = converted
    vol_charge = 0.0
    tier_lines = []

    for t in tiers:
        if remaining <= 0:
            break
        from_qty = t.get("from", 0)
        to_qty = t.get("to")
        price = t["price"]
        used = min(remaining, to_qty - from_qty) if to_qty is not None else remaining
        charge = used * price
        vol_charge += charge

        used_end = from_qty + used
        range_str = f"{from_qty:g}–{used_end:.2f} {ul}" if to_qty is None or used < (to_qty - from_qty) else f"{from_qty:g}–{to_qty:g} {ul}"
        tier_lines.append(f"  {range_str}  ×  ${price:.4f}/{ul}  =  ${charge:.2f}")
        remaining -= used

    lines.extend(tier_lines)

    if period > 1 and tier_lines:
        lines.append(f"  Subtotal: ${vol_charge:.2f} {pl} ÷ {period} = ${vol_charge/period:.2f}/mo")

    # Total
    fixed_mo = fixed / period
    vol_mo = vol_charge / period
    total = fixed_mo + vol_mo
    if fixed and tier_lines:
        lines.append(f"Total: ${fixed_mo:.2f} + ${vol_mo:.2f} = ${total:.2f}/mo")
    else:
        lines.append(f"Total: ${total:.2f}/mo")

    return lines
