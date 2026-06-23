"""Shared chrome for the wizard pages: card container style + step indicator."""

import streamlit as st

CARD_STYLE = """
    <style>
        .st-key-container {
            padding: 40px !important;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        }
    </style>
"""

STEPS = [
    "Welcome",
    "Configure & Upload",
    "Extraction",
    "Validation",
    "Benchmark Bill",
    "Results",
]


def render_header(current_step: int) -> None:
    """Card style + step indicator + title. current_step is 1-indexed, matching STEPS."""
    st.markdown(CARD_STYLE, unsafe_allow_html=True)

    st.html("""
    <div style="text-align: center; margin-bottom: 2rem;">
      <h1 style="display: inline; font-size: 2rem; font-weight: 600; margin: 0;">
        tariff-extractor
      </h1>
      <span style="font-size: 1em; color: gray;">(playground)</span>
    </div>
    """)

    circles = []
    for i, label in enumerate(STEPS, start=1):
        if i < current_step:
            bg, fg, content = "black", "white", "&#10003;"
        elif i == current_step:
            bg, fg, content = "black", "white", str(i)
        else:
            bg, fg, content = "#e5e7eb", "#374151", str(i)
        circles.append(f"""
        <div style="display: flex; flex-direction: column; align-items: center; text-align: center; color: #6b7280;">
          <div style="width: 40px; height: 40px; border-radius: 50%; background-color: {bg}; color: {fg}; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: bold;">
            {content}
          </div>
          <div style="margin-top: 10px; font-size: 12px;">{label}</div>
        </div>
        """)

    st.html(f"""<body>
      <div style="display: flex; justify-content: center; padding: 10px; gap: 40px; flex-wrap: wrap;">
        {''.join(circles)}
      </div>
    </body>""")


def reset_session() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
