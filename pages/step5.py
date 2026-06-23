import streamlit as st

from wizard_ui import render_header, reset_session

with st.container(border=False, key="container"):
    render_header(6)

    st.markdown("**Results**")

    if not st.session_state.get("bill_result"):
        st.warning("Compute a benchmark bill first.")
        if st.button("Back to benchmark bill"):
            st.switch_page("pages/step4.py")
        st.stop()

    result = st.session_state.validation_result
    br = st.session_state.bill_result
    badge = "🟢" if result["confidence"] == "model_estimate" else "🔴"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Utility", st.session_state.get("utility_name") or "—")
    with col2:
        st.metric("Confidence", f"{badge} {result['confidence']}")
    with col3:
        st.metric(f"Bill at {st.session_state.bill_volume:,} gal/month", f"${br['monthly_bill']:.2f}")

    st.divider()

    button_container = st.columns([3, 1])
    with button_container[0]:
        st.text(f"Extracted with {st.session_state.get('model_used', 'unknown model')}.")
    with button_container[1]:
        st.download_button(
            label="Download tariff.json",
            data=st.session_state.tariff_json,
            file_name="tariff.json",
            mime="application/json",
        )

    st.divider()

    containers = st.columns(4, gap="large")
    with containers[0]:
        if st.button("Home", type="secondary", key="back_button"):
            reset_session()
            st.switch_page("main.py")
    with containers[3]:
        if st.button("Start Over", type="primary", key="next_button"):
            reset_session()
            st.switch_page("pages/step1.py")
