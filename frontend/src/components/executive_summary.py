"""Executive summary KPI row (PDF section 1)."""

from __future__ import annotations

import streamlit as st


def render_executive_summary(summary: dict) -> None:
    st.subheader("Executive Summary")
    cols = st.columns(5)
    cols[0].metric("Total Customers", summary.get("total_customers", 0))
    cols[1].metric("🟢 Healthy", summary.get("healthy_count", 0))
    cols[2].metric("🟡 Upsell Opportunities", summary.get("upsell_count", 0))
    cols[3].metric("🔴 At Risk", summary.get("at_risk_count", 0))
    cols[4].metric("Average Risk Score", f"{summary.get('average_risk_score', 0):.1f}")
