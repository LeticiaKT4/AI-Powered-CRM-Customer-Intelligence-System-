"""Streamlit session state helpers."""

import streamlit as st


def init_session() -> None:
    defaults = {
        "sidebar_collapsed": False,
        "layout": None,
        "layout_initialized": False,
        "analysis_history": [],
        "selected_widget_id": None,
        "last_degraded_warning": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
