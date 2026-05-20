"""Stale-data warning when API returns degraded mode (FR-011)."""

import streamlit as st


def render_degraded_banner(payload: dict | None) -> None:
    if not payload or not payload.get("degraded"):
        return
    warning = payload.get("warning") or "Data may be stale."
    cached_at = payload.get("cached_at")
    msg = warning
    if cached_at:
        msg = f"{warning} (cached at {cached_at})"
    st.warning(msg)
