"""Session-only dashboard layout editor (FR-004)."""

from __future__ import annotations

import streamlit as st

WIDGET_TYPES = ["bar", "line", "pie", "table", "metric"]


def render_layout_editor(layout: dict) -> dict:
    st.subheader("Customize layout (this session)")
    widgets = layout.setdefault("widgets", [])

    with st.expander("Add widget"):
        wtype = st.selectbox("Widget type", WIDGET_TYPES, key="add_wtype")
        title = st.text_input("Title", value="New Widget")
        if st.button("Add"):
            new_id = f"w_{len(widgets) + 1}"
            metric_keys = ["pipeline_by_stage"] if wtype != "table" else ["opportunity_table"]
            config = {"object_name": "Opportunity"} if wtype == "table" else {}
            widgets.append(
                {
                    "widget_id": new_id,
                    "widget_type": wtype,
                    "title": title,
                    "metric_keys": metric_keys,
                    "position": len(widgets),
                    "config": config,
                    "visible": True,
                }
            )
            st.rerun()

    for idx, w in enumerate(sorted(widgets, key=lambda x: x.get("position", 0))):
        cols = st.columns([4, 1, 1])
        cols[0].markdown(f"**{w.get('title')}** ({w.get('widget_type')})")
        if cols[1].button("Up", key=f"up_{w['widget_id']}") and idx > 0:
            widgets[idx]["position"], widgets[idx - 1]["position"] = widgets[idx - 1]["position"], widgets[idx]["position"]
            st.rerun()
        if cols[2].button("Remove", key=f"rm_{w['widget_id']}"):
            widgets.pop(idx)
            for i, item in enumerate(widgets):
                item["position"] = i
            st.rerun()

    st.session_state["layout"] = layout
    return layout
