import streamlit as st

from wizard_ui import render_header

with st.container(border=False, key="container"):
    render_header(2)

    st.markdown("**Configure & upload**")
    st.markdown(
        "Bring your own OpenAI-compatible API key, then upload a rate document (PDF) "
        "or paste HTML/text. Native PDF support requires a model/provider that accepts "
        "file content blocks — Gemini via OpenRouter is known to work."
    )

    st.text_input("Base URL", value=st.session_state.get("base_url", "https://openrouter.ai/api/v1"), key="base_url")
    st.text_input("API key", value=st.session_state.get("api_key", ""), type="password", key="api_key")
    st.text_input("Model", value=st.session_state.get("model", "google/gemini-3-flash-preview"), key="model")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Rate document (PDF)", type=["pdf"])
    with col2:
        html_text = st.text_area(
            "...or paste HTML / text",
            value=st.session_state.get("html_text") or "",
            height=150,
        )
    utility_name = st.text_input("Utility name (optional)", value=st.session_state.get("utility_name", ""))

    containers = st.columns(5, gap="large")
    with containers[0]:
        if st.button("Go Home", type="secondary", key="back_button"):
            st.switch_page("main.py")
    with containers[4]:
        if st.button("Next", type="primary", key="next_button"):
            if not st.session_state.get("api_key"):
                st.error("Enter an API key before continuing.")
            elif not uploaded and not html_text:
                st.error("Upload a PDF or paste HTML/text before continuing.")
            else:
                st.session_state.pdf_bytes = uploaded.read() if uploaded else None
                st.session_state.html_text = html_text or None
                st.session_state.utility_name = utility_name
                # Clear downstream state so step2 re-runs extraction for the new input
                for key in ("tariff_json", "model_used", "validation_result", "bill_result"):
                    st.session_state.pop(key, None)
                st.switch_page("pages/step2.py")
