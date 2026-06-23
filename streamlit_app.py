"""Interactive playground for tariff_extractor.

Upload a water rate document and step through extraction, validation,
and benchmark bill calculation — with the raw output of every stage
visible and editable.

Run with: streamlit run streamlit_app.py
"""

import json

import streamlit as st
from openai import OpenAI

from tariff_extractor import bill_explanation, compute_bill, extract, validate

st.set_page_config(page_title="Tariff Extractor Playground", layout="wide")

DEFAULTS = {
    "tariff_json": None,
    "model_used": None,
    "validation_result": None,
    "bill_result": None,
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)

st.title("Tariff Extractor Playground")
st.caption(
    "Upload a water rate document (PDF or pasted HTML/text) and walk through "
    "extraction → validation → benchmark bill, step by step. Every intermediate "
    "JSON output is editable — use it to see how the pipeline reacts to changes."
)

with st.sidebar:
    st.header("LLM configuration")
    base_url = st.text_input("Base URL", value="https://openrouter.ai/api/v1")
    api_key = st.text_input("API key", type="password", help="Never stored — used only for this session.")
    model = st.text_input("Model", value="google/gemini-3-flash-preview")
    st.caption(
        "Any OpenAI-compatible provider works. Native PDF upload requires a "
        "model/provider that supports file content blocks (Gemini via "
        "OpenRouter is known to work)."
    )
    st.divider()
    if st.button("Start over"):
        for key in DEFAULTS:
            st.session_state[key] = DEFAULTS[key]
        st.rerun()


def get_client() -> OpenAI:
    if not api_key:
        st.error("Enter an API key in the sidebar to continue.")
        st.stop()
    return OpenAI(base_url=base_url, api_key=api_key)


# ── Step 1: upload & extract ────────────────────────────────────────────────

st.header("Step 1 — Upload & extract")

col1, col2 = st.columns(2)
with col1:
    uploaded = st.file_uploader("Rate document (PDF)", type=["pdf"])
with col2:
    html_text = st.text_area("...or paste HTML / text", height=150)
utility_name = st.text_input("Utility name (optional, included in the prompt for context)")

if st.button("Run extraction", type="primary", disabled=not (uploaded or html_text)):
    client = get_client()
    pdf_bytes = uploaded.read() if uploaded else None
    with st.spinner(f"Calling {model}..."):
        try:
            tariff, model_used = extract(
                client,
                model,
                pdf_bytes=pdf_bytes,
                html_text=html_text or None,
                utility_name=utility_name,
            )
        except Exception as e:
            st.exception(e)
            st.stop()
    st.session_state.tariff_json = json.dumps(tariff, indent=2)
    st.session_state.model_used = model_used
    st.session_state.validation_result = None
    st.session_state.bill_result = None

if st.session_state.tariff_json:
    st.success(f"Extracted with `{st.session_state.model_used}`")
    st.subheader("Raw extracted tariff JSON")
    st.caption("Edit freely — downstream steps use whatever is in this box.")
    st.session_state.tariff_json = st.text_area(
        "tariff.json",
        value=st.session_state.tariff_json,
        height=350,
        label_visibility="collapsed",
    )

# ── Step 2: validate ─────────────────────────────────────────────────────────

if st.session_state.tariff_json:
    st.header("Step 2 — Validate")

    if st.button("Run validation", type="primary"):
        try:
            tariff = json.loads(st.session_state.tariff_json)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
            st.stop()
        bill_amount, _ = compute_bill(tariff)
        st.session_state.validation_result = validate(tariff, bill=bill_amount)
        st.session_state.bill_result = None

    result = st.session_state.validation_result
    if result:
        badge = "🟢" if result["confidence"] == "model_estimate" else "🔴"
        st.subheader(f"{badge} confidence: {result['confidence']} (score {result['score']})")
        st.caption("Raw validate() output — hard checks, scored checklist, and reasons.")
        st.json(result)

# ── Step 3: benchmark bill ───────────────────────────────────────────────────

if st.session_state.validation_result:
    st.header("Step 3 — Benchmark bill")

    volume = st.number_input("Volume (gallons/month)", value=6000, step=500, min_value=0)

    if st.button("Compute bill", type="primary"):
        try:
            tariff = json.loads(st.session_state.tariff_json)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
            st.stop()
        monthly_bill, seasonal_breakdown = compute_bill(tariff, volume_gal=volume)
        explanation = bill_explanation(tariff, volume_gal=volume)
        st.session_state.bill_result = {
            "monthly_bill": monthly_bill,
            "seasonal_breakdown": seasonal_breakdown,
            "explanation": explanation,
        }

    br = st.session_state.bill_result
    if br:
        st.metric(f"Bill at {volume:,} gal/month", f"${br['monthly_bill']:.2f}")

        if br["seasonal_breakdown"]:
            st.subheader("Seasonal breakdown")
            st.caption("Raw compute_bill() seasonal output.")
            st.json(br["seasonal_breakdown"])

        st.subheader("Step-by-step explanation")
        st.caption("Raw bill_explanation() output.")
        for line in br["explanation"]:
            st.text(line)
