import json

import streamlit as st

from tariff_extractor import compute_bill, validate
from wizard_ui import render_header

with st.container(border=False, key="container"):
    render_header(4)

    st.markdown("**Validation**")

    if not st.session_state.get("tariff_json"):
        st.warning("Run extraction first.")
        if st.button("Back to extraction"):
            st.switch_page("pages/step2.py")
        st.stop()

    if st.session_state.get("validation_result") is None:
        try:
            tariff = json.loads(st.session_state.tariff_json)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
            if st.button("Back to extraction"):
                st.switch_page("pages/step2.py")
            st.stop()
        bill_amount, _ = compute_bill(tariff)
        st.session_state.validation_result = validate(tariff, bill=bill_amount)

    result = st.session_state.validation_result
    badge = "🟢" if result["confidence"] == "model_estimate" else "🔴"
    st.subheader(f"{badge} confidence: {result['confidence']} (score {result['score']})")
    st.markdown("Raw `validate()` output — hard checks, scored checklist, and reasons.")
    st.json(result)

    containers = st.columns(5, gap="large")
    with containers[0]:
        if st.button("Back", type="secondary", key="back_button"):
            st.switch_page("pages/step2.py")
    with containers[1]:
        if st.button("Re-run validation", type="secondary", key="rerun_button"):
            st.session_state.validation_result = None
            st.rerun()
    with containers[4]:
        if st.button("Next", type="primary", key="next_button"):
            st.session_state.pop("bill_result", None)
            st.switch_page("pages/step4.py")
