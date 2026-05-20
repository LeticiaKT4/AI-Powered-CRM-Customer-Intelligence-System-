"""Paginated table renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from api_client import get_records


def render_table(widget: dict) -> dict | None:
    config = widget.get("config") or {}
    object_name = config.get("object_name", "Opportunity")
    title = widget.get("title", object_name)

    st.subheader(title)
    page = st.number_input(f"Page ({object_name})", min_value=1, value=1, key=f"page_{widget['widget_id']}")
    page_size = st.selectbox("Rows", [25, 50, 100], index=1, key=f"ps_{widget['widget_id']}")

    try:
        payload = get_records(object_name, page=int(page), page_size=int(page_size))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load records: {exc}")
        return None

    rows = payload.get("rows", [])
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No records to display.")
    return payload
