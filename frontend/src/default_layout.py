"""Load default dashboard layout seed into session."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

def _resolve_layout_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "data" / "default_layout.json"


def ensure_layout_loaded() -> dict:
    if st.session_state.get("layout_initialized") and st.session_state.get("layout"):
        return st.session_state["layout"]

    path = _resolve_layout_path()
    with path.open(encoding="utf-8") as f:
        layout = json.load(f)
    st.session_state["layout"] = layout
    st.session_state["layout_initialized"] = True
    return layout
