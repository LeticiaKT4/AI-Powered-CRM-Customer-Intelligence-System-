"""Customer detail panel (PDF section 3)."""

from __future__ import annotations

import streamlit as st


def _status_badge(status: str) -> str:
    icons = {"Healthy": "🟢", "At Risk": "🔴", "Upsell": "🟡"}
    return f"{icons.get(status, '')} **{status}**"


def render_customer_detail(detail: dict) -> None:
    st.subheader(f"Customer Detail — {detail.get('company_name', '')}")
    st.markdown(_status_badge(detail.get("status", "")))

    col_profile, col_ai = st.columns(2)

    with col_profile:
        st.markdown("#### Profile")
        profile = detail.get("profile") or {}
        st.markdown(f"**Industry:** {detail.get('industry', '—')}")
        st.markdown(f"**Plan type:** {detail.get('plan_type', '—')}")
        if profile.get("annual_revenue"):
            st.markdown(f"**Annual revenue:** ${profile['annual_revenue']:,.0f}")
        if profile.get("region"):
            st.markdown(f"**Region:** {profile['region']}")

        st.markdown("#### Usage metrics")
        for m in detail.get("usage_metrics") or []:
            delta = m["current"] - m["previous"]
            st.metric(
                m.get("label", "Metric"),
                f"{m['current']:.0f}{m.get('unit', '') if m.get('unit') == '%' else ''}",
                delta=f"{delta:+.0f}",
            )

    with col_ai:
        st.markdown("#### AI Explanation")
        st.info(detail.get("ai_explanation", ""))
        factors = detail.get("contributing_factors") or []
        if factors:
            st.markdown("**Key contributing factors**")
            for f in factors:
                st.markdown(f"- {f}")

    st.markdown("#### Change Detection")
    signals = detail.get("change_signals") or []
    if signals:
        for s in signals:
            icon = "⚠" if s.get("severity") in ("warning", "critical") else "ℹ"
            st.warning(f"{icon} {s.get('message', '')}") if s.get("severity") != "info" else st.info(s.get("message", ""))
    else:
        st.success("No significant negative changes detected.")

    conf = detail.get("confidence", "MEDIUM")
    conf_pct = detail.get("confidence_pct", 0)
    st.markdown(f"#### Confidence Score: **{conf}** ({conf_pct:.0f}%)")

    actions = detail.get("recommended_actions") or []
    if actions:
        st.markdown("#### Recommended Actions")
        for a in actions:
            st.markdown(f"- {a}")
