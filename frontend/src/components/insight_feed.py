"""AI insight feed (PDF section 5)."""

from __future__ import annotations

import streamlit as st


def render_insight_feed(items: list[dict]) -> None:
    st.subheader("AI Insight Feed")
    if not items:
        st.caption("No insights at this time.")
        return

    for item in items:
        icon = item.get("icon", "•")
        message = item.get("message", "")
        st.markdown(f"{icon} {message}")
