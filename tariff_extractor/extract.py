import re
import json
import base64
from pathlib import Path
from datetime import date

SCHEMA_DIR = Path(__file__).parent / "schema"


def extract(
    client,
    model: str,
    *,
    pdf_bytes: bytes | None = None,
    html_text: str | None = None,
    utility_name: str = "",
) -> tuple[dict, str]:
    """Extract tariff JSON from a document using the provided OpenAI-compatible client.

    PDF is sent natively as a file block (full document, no page rendering).
    HTML is sent as text. Returns (tariff_dict, model_name).

    Args:
        client: An openai.OpenAI (or compatible) client instance.
        model: Model identifier string (e.g. "google/gemini-3-flash-preview").
        pdf_bytes: Raw PDF bytes, or None.
        html_text: HTML/text content, or None.
        utility_name: Optional utility name included in the prompt for context.

    Returns:
        A tuple of (tariff_dict, model_name) where tariff_dict conforms to
        tariff.schema.json and model_name is the model string used.
    """
    schema = json.loads((SCHEMA_DIR / "tariff.schema.json").read_text())
    examples = "\n\n".join(
        f"### {f.stem}\n```json\n{f.read_text().strip()}\n```"
        for f in sorted((SCHEMA_DIR / "examples").glob("*.json"))
    )

    system_prompt = (
        "You are a water rate extraction assistant. "
        "Extract residential water rate information into the tariff JSON format below.\n\n"
        f"Today's date is {date.today().isoformat()}. Extract rates currently in effect.\n\n"
        "Focus on: residential customer class, smallest meter size available.\n\n"
        "## Verbatim numbers — critical rule\n"
        "Every numeric value in the output (fixed_charge, tier prices, tier boundaries) "
        "must appear verbatim as a standalone number in the source document. "
        "Never add, subtract, or multiply values together to produce a tier price. "
        "If a schedule lists a 'User Charge' and a separate 'Environmental Charge' or "
        "'Infrastructure Surcharge' per unit, use only the User Charge as the tier price — "
        "do not add the surcharge to the tier price. Surcharges are excluded from our bill calculation.\n\n"
        "## Included-water base charges\n"
        "Some utilities bundle a block of water into the monthly service charge "
        "(e.g. 'service charge includes 5 CCF'). Set `fixed_charge` to the stated service charge "
        "dollar amount. Model tiers starting from 0 using verbatim per-unit rates from the source "
        "for all consumption — do not try to model the included block separately.\n\n"
        "## Unit conversion\n"
        "Report `unit` as: 'ccf' for per-hundred-cubic-feet, 'hcf' for per-hundred-cubic-feet "
        "(alternate label), 'kgal' for per-thousand-gallons, 'gal' for per-gallon, "
        "'cf' for per-cubic-foot, 'm3' for per-cubic-meter. "
        "Use the unit exactly as labeled in the source. "
        "If the source shows rates per 1,000 cubic feet, divide by 10 to convert to ccf. "
        "If the source shows both CCF and per-1,000-gallon columns, prefer kgal — it requires no conversion and traces directly.\n\n"
        "## Pricing zones\n"
        "Always extract the standard in-district, inside-city, or within-service-area residential rate. "
        "Do not use outside-city or out-of-district rates — those are billing surcharges for non-residents, "
        "not representative of the utility's customer base.\n"
        "Geographic pressure zones (Zone A/B, Zone 1/2, High Service Area, Low Service Area) are different: "
        "these reflect elevation or infrastructure differences within the service area. If these exist, set "
        "`has_multiple_zones` to true and extract the BASE zone (Zone 1, Low Service Area, or whichever is "
        "labeled as the standard or default zone), recording its name exactly as it appears in the source "
        "in the `zone` field. The base zone represents the typical customer and is the standard for "
        "cross-utility comparisons.\n"
        "If only one zone exists or zones are not mentioned, omit both `zone` and `has_multiple_zones`.\n\n"
        "## Tier boundaries\n"
        "Express tier boundaries as **absolute cumulative volume thresholds**, not incremental volumes.\n"
        "- 'First 4,000 gallons' → from: 0, to: 4000\n"
        "- 'Next 4,000 gallons (4,001–8,000)' → from: 4000, to: 8000\n"
        "- 'Over 8,000 gallons' → from: 8000, to: null\n"
        "The `from` of each tier must equal the `to` of the previous tier. "
        "If the source only lists an upper bound per tier (e.g. 'up to 10 CCF: $X / 10–20 CCF: $Y'), "
        "read the upper bound of tier N as the `from` for tier N+1. "
        "Never set multiple tiers all to `from: 0` — that means boundaries were not extracted. "
        "If a boundary is genuinely ambiguous, omit `to` (leave it null) rather than guessing.\n"
        "CRITICAL: tier boundaries must be in the SAME unit as `unit`. If the source shows boundaries "
        "in gallons but the price is per kgal, divide boundaries by 1,000. If boundaries are in CCF "
        "but price is per gallon, multiply by 748. Always check that boundaries are consistent with "
        "the rate unit — a boundary of 6,000 with unit='kgal' means 6 million gallons, which is wrong "
        "for residential.\n\n"
        "## Billing frequency\n"
        "Set `bill_frequency` to 'monthly', 'bimonthly', or 'quarterly' as stated in the source. "
        "Extract all numeric values (fixed_charge, tier boundaries, tier prices) verbatim as they appear "
        "in the source — do not convert them to monthly equivalents. The bill calculator handles "
        "normalization. For example, if a bimonthly schedule shows a $20 service charge and tier "
        "boundaries of 10 CCF / 20 CCF, extract exactly those values; do not halve them.\n\n"
        f"## Schema\n```json\n{json.dumps(schema, indent=2)}\n```\n\n"
        f"## Examples\n{examples}\n\n"
        "Output ONLY valid JSON matching the schema. No explanation, no markdown fences."
    )

    label = f" for {utility_name}" if utility_name else ""

    if pdf_bytes:
        b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
        user_content = [
            {"type": "text", "text": f"Extract the water rates from this document{label}."},
            {
                "type": "file",
                "file": {
                    "filename": "rates.pdf",
                    "file_data": f"data:application/pdf;base64,{b64}",
                },
            },
        ]
    else:
        user_content = f"Extract the water rates{label}:\n\n{html_text or ''}"

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    raw = response.choices[0].message.content
    raw = re.sub(r"^```(?:json)?\s*\n?", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\n?```\s*$", "", raw, flags=re.MULTILINE)
    return json.loads(raw), model
