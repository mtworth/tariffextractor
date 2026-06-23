import json

import streamlit as st

from tariff_extractor import bill_explanation, compute_bill
from wizard_ui import render_header

with st.container(border=False, key="container"):
    render_header(5)

    st.markdown("**Benchmark bill**")

    if not st.session_state.get("validation_result"):
        st.warning("Run validation first.")
        if st.button("Back to validation"):
            st.switch_page("pages/step3.py")
        st.stop()

    volume = st.number_input("Volume (gallons/month)", value=6000, step=500, min_value=0, key="bill_volume")

    if st.session_state.get("bill_result") is None or st.session_state.get("bill_result_volume") != volume:
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
        st.session_state.bill_result_volume = volume

    br = st.session_state.bill_result
    st.metric(f"Bill at {volume:,} gal/month", f"${br['monthly_bill']:.2f}")

    if br["seasonal_breakdown"]:
        st.markdown("Raw `compute_bill()` seasonal output.")
        st.json(br["seasonal_breakdown"])

    st.markdown("Raw `bill_explanation()` output.")
    for line in br["explanation"]:
        st.text(line)

    containers = st.columns(5, gap="large")
    with containers[0]:
        if st.button("Back", type="secondary", key="back_button"):
            st.switch_page("pages/step3.py")
    with containers[1]:
        if st.button("Recompute", type="secondary", key="recompute_button"):
            st.session_state.bill_result = None
            st.rerun()
    with containers[4]:
        if st.button("Next", type="primary", key="next_button"):
            st.switch_page("pages/step5.py")
