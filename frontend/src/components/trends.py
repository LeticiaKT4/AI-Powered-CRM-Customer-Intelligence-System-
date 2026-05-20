"""Trends and insights charts (PDF section 4)."""

from __future__ import annotations

import plotly.express as px
import streamlit as st


def render_trends(trends: dict) -> None:
    st.subheader("Trends / Insights")
    c1, c2, c3 = st.columns(3)

    risk = trends.get("risk_distribution") or []
    status = trends.get("status_counts") or []
    usage = trends.get("usage_trend") or []

    with c1:
        if risk:
            fig = px.pie(
                names=[p["label"] for p in risk],
                values=[p["value"] for p in risk],
                title="Risk distribution",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No risk data")

    with c2:
        if usage:
            fig = px.line(
                x=[p["label"] for p in usage],
                y=[p["value"] for p in usage],
                labels={"x": "Month", "y": "Avg usage index"},
                title="Usage trend over time",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No usage trend data")

    with c3:
        if status:
            fig = px.bar(
                x=[p["label"] for p in status],
                y=[p["value"] for p in status],
                labels={"x": "Status", "y": "Customers"},
                title="Customers by status",
                color=[p["label"] for p in status],
                color_discrete_map={
                    "Healthy": "#2E844A",
                    "Upsell": "#FFB75D",
                    "At Risk": "#C23934",
                },
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No status data")
