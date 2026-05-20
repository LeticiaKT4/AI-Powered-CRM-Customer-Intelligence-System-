"""Plotly chart renderers for dashboard widgets."""

from __future__ import annotations

from typing import Any

import plotly.express as px
import streamlit as st


def render_chart(widget: dict, metrics_payload: dict) -> None:
    points = metrics_payload.get("data_points", [])
    key = widget.get("metric_keys", ["pipeline_by_stage"])[0]
    filtered = [p for p in points if p.get("metric_key") == key]

    if not filtered:
        st.info("No metric data available for this chart.")
        return

    labels = [p.get("label", p.get("metric_key", "")) for p in filtered]
    values = [float(p.get("value", 0)) for p in filtered]

    widget_type = widget.get("widget_type", "bar")
    title = widget.get("title", "Chart")

    if widget_type == "line":
        fig = px.line(x=labels, y=values, labels={"x": "Category", "y": "Value"}, title=title)
    elif widget_type == "pie":
        fig = px.pie(names=labels, values=values, title=title)
    else:
        fig = px.bar(x=labels, y=values, labels={"x": "Category", "y": "Value"}, title=title)

    fig.update_traces(hovertemplate="%{x}: %{y}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)
