import json

import streamlit as st
from openai import OpenAI

from tariff_extractor import extract
from wizard_ui import render_header

with st.container(border=False, key="container"):
    render_header(3)

    st.markdown("**Extraction**")

    if not st.session_state.get("pdf_bytes") and not st.session_state.get("html_text"):
        st.warning("Upload a document first.")
        if st.button("Back to upload"):
            st.switch_page("pages/step1.py")
        st.stop()

    if st.session_state.get("tariff_json") is None:
        client = OpenAI(base_url=st.session_state.base_url, api_key=st.session_state.api_key)
        with st.spinner(f"Calling {st.session_state.model}..."):
            try:
                tariff, model_used = extract(
                    client,
                    st.session_state.model,
                    pdf_bytes=st.session_state.get("pdf_bytes"),
                    html_text=st.session_state.get("html_text"),
                    utility_name=st.session_state.get("utility_name", ""),
                )
            except Exception as e:
                st.error(f"Extraction failed: {e}")
                if st.button("Back to upload"):
                    st.switch_page("pages/step1.py")
                st.stop()
        st.session_state.tariff_json = json.dumps(tariff, indent=2)
        st.session_state.model_used = model_used

    st.success(f"Extracted with `{st.session_state.model_used}`")
    st.markdown("Raw extracted tariff JSON — edit freely, downstream steps use whatever is in this box.")
    st.session_state.tariff_json = st.text_area(
        "tariff.json",
        value=st.session_state.tariff_json,
        height=350,
        label_visibility="collapsed",
    )

    containers = st.columns(5, gap="large")
    with containers[0]:
        if st.button("Back", type="secondary", key="back_button"):
            st.switch_page("pages/step1.py")
    with containers[1]:
        if st.button("Re-run extraction", type="secondary", key="rerun_button"):
            st.session_state.tariff_json = None
            st.rerun()
    with containers[4]:
        if st.button("Next", type="primary", key="next_button"):
            try:
                json.loads(st.session_state.tariff_json)
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
                st.stop()
            st.session_state.pop("validation_result", None)
            st.session_state.pop("bill_result", None)
            st.switch_page("pages/step3.py")
