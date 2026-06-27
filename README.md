# tariff-extractor

Extract residential water tariffs from PDFs or HTML into structured JSON, validate the output, and compute benchmark bills.

## What it does

Given a water utility rate document (PDF or HTML), `tariff-extractor`:

1. **Extracts** the rate structure into a typed JSON tariff object (fixed charges, volumetric tiers, billing frequency, unit)
2. **Validates** the result with hard checks (unit plausibility, gapless tier boundaries, bill sanity) and a scored checklist
3. **Computes** a normalized 6,000-gallon/month benchmark bill with a human-readable step-by-step explanation

All extraction logic is prompt-based and model-agnostic — any OpenAI-compatible provider works. Native PDF support (sending the file as a base64 block rather than extracted text) requires a model/provider that supports it; Gemini via OpenRouter works well.

## Install

```bash
# From PyPI (once published)
pip install tariff-extractor

# From GitHub
pip install git+https://github.com/maxwelltitsworth/tariffextractor.git
```

## Quick usage

```python
from openai import OpenAI
from tariff_extractor import extract, validate, compute_bill, bill_explanation

# Initialize an OpenAI-compatible client
# OpenRouter example (supports Gemini native PDF):
client = OpenAI(
    api_key="your-openrouter-key",
    base_url="https://openrouter.ai/api/v1",
)

model = "google/gemini-3-flash-preview"

# Extract from a PDF
pdf_bytes = open("rates.pdf", "rb").read()
tariff, model_used = extract(client, model, pdf_bytes=pdf_bytes, utility_name="Springfield Water")

# Or from HTML
# tariff, model_used = extract(client, model, html_text=html_string)

# Validate
bill_amount, _ = compute_bill(tariff)
result = validate(tariff, bill=bill_amount)
print(result["confidence"])   # "model_estimate" or "flagged"
print(result["score"])        # 0.0–1.0

# Compute benchmark bill at 6,000 gal/month
monthly_bill, seasonal_breakdown = compute_bill(tariff)
print(f"${monthly_bill:.2f}/month")

# Step-by-step explanation
for line in bill_explanation(tariff):
    print(line)
```

## Try it

An interactive extractor is available at [whatwatercosts.org/extractor](https://whatwatercosts.org/extractor) — upload a rate PDF or paste HTML and step through extraction, validation, and benchmark bill calculation in your browser.

## Output format

The `extract()` function returns a tariff dict conforming to [`tariff_extractor/schema/tariff.schema.json`](tariff_extractor/schema/tariff.schema.json). Key fields:

| Field | Description |
|---|---|
| `utility_name` | Name as it appears in the source document |
| `customer_class` | Always `"residential"` for standard extraction |
| `unit` | Source billing unit: `ccf`, `kgal`, `gal`, `hcf`, `cf`, or `m3` |
| `bill_frequency` | `monthly`, `bimonthly`, or `quarterly` |
| `fixed_charge` | Monthly/periodic service charge in dollars |
| `volumetric.type` | `tiered`, `flat`, or `seasonal_flat` |
| `volumetric.tiers` | Array of `{from, to, price, season}` objects |
| `effective_date` | ISO date string (`YYYY-MM-DD`) if present in source |

See [`schema/examples/`](tariff_extractor/schema/examples/) for sample outputs covering flat, tiered, and seasonal-flat rate structures.

## Notes

- Native PDF support (sending the PDF as a file block rather than extracted text) requires a model and provider that supports the `file` content block type. Gemini Flash via OpenRouter is the recommended choice.
- All numeric values are extracted verbatim from the source document — no arithmetic is performed during extraction.
- Tier boundaries are stored as absolute cumulative volume thresholds in the source unit.
- The benchmark bill normalizes bimonthly and quarterly schedules to a monthly equivalent for cross-utility comparison.
