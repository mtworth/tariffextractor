import streamlit as st

st.set_page_config(page_title="Tariff Extractor Playground", layout="centered")

st.markdown("###")

st.html("""
<body style="background-color: rgb(255, 255, 255); min-height: 60vh; display: flex; align-items: center; justify-content: center; font-family: 'Inter', sans-serif;">
  <main style="display: flex; flex-direction: column; align-items: center; width: 100%; padding-left: 1rem; padding-right: 1rem;">
    <h1 style="margin-bottom: 2rem; font-size: 2rem; font-weight: 600; text-align: center;">tariff-extractor</h1>
    <h2 style="text-align: center; font-weight: 900; font-size: 3rem; line-height: 1.25; margin-bottom: 2rem;">
      Water rate documents, <span style="position: relative; display: inline-block;">
        <span style="position: relative; z-index: 10;">structured</span>
        <span style="position: absolute; left: 0; bottom: 0.25rem; width: 100%; height: 0.75rem; background-color: rgb(254, 240, 138); z-index: 0; border-radius: 0.125rem;"></span>
      </span>
    </h2>
    <p style="text-align: center; color: rgb(75, 85, 99); font-size: 1.25rem; max-width: 42rem; margin-bottom: 3rem;">
        Upload a residential water rate PDF or HTML page and watch it walk through extraction, validation, and benchmark bill calculation — every raw intermediate output is visible and editable.
    </p>
  </main>
</body>""")

columns = st.columns(4, gap="medium")
with columns[1]:
    if st.button("Try the demo!", key="get_started", type="primary", use_container_width=True):
        st.switch_page("pages/step1.py")
with columns[2]:
    st.link_button("View on GitHub", "https://github.com/mtworth/tariffextractor", use_container_width=True)
