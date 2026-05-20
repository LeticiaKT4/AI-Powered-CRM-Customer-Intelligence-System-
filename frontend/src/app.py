"""AI CRM Dashboard — customer health layout per product spec."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st

from api_client import (
    get_customer_detail,
    get_customer_insights,
    get_customer_trends,
    get_customers,
    get_health,
)
from components.customer_detail import render_customer_detail
from components.customer_table import render_customer_filters, render_customer_table
from components.degraded_banner import render_degraded_banner
from components.executive_summary import render_executive_summary
from components.insight_feed import render_insight_feed
from components.sidebar_ai import render_sidebar
from components.trends import render_trends
from analysis_context import build_analysis_context
from session import init_session

st.set_page_config(
    page_title="CRM Customer Health Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_FILTERS = {
    "search": None,
    "status": None,
    "sort_by": "risk_score",
    "sort_dir": "desc",
}


@st.cache_data(ttl=60)
def fetch_customers(
    status: str | None,
    search: str | None,
    sort_by: str,
    sort_dir: str,
) -> dict:
    return get_customers(status=status, search=search, sort_by=sort_by, sort_dir=sort_dir)


@st.cache_data(ttl=60)
def fetch_trends() -> dict:
    return get_customer_trends()


@st.cache_data(ttl=60)
def fetch_insights() -> dict:
    return get_customer_insights()


@st.cache_data(ttl=60)
def fetch_detail(customer_id: str) -> dict:
    return get_customer_detail(customer_id)


def main() -> None:
    init_session()

    try:
        health = get_health()
        mode = health.get("crm_data_mode", "unknown")
    except Exception:
        mode = "unreachable"

    st.title("CRM Customer Health Dashboard")
    data_source = health.get("data_source", mode)
    counts = health.get("record_counts") or {}
    count_summary = ", ".join(f"{k}: {v}" for k, v in counts.items()) if counts else "n/a"
    st.caption(
        f"Mode: {mode} · Source: {data_source} · Records: {count_summary} · "
        f"Benchmark tasks: {health.get('benchmark_tasks', 0)}"
    )

    filters = st.session_state.get("cust_filters", DEFAULT_FILTERS.copy())
    customers_payload: dict = {}
    try:
        customers_payload = fetch_customers(
            status=filters.get("status"),
            search=filters.get("search"),
            sort_by=filters.get("sort_by", "risk_score"),
            sort_dir=filters.get("sort_dir", "desc"),
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Cannot load customers: {exc}")
        return

    render_degraded_banner(customers_payload)

    # Section 1: Executive Summary
    render_executive_summary(customers_payload.get("executive_summary", {}))
    st.divider()

    # Section 2: Customer Table
    new_filters = render_customer_filters()
    if new_filters != filters:
        st.session_state["cust_filters"] = new_filters
        fetch_customers.clear()
        st.rerun()

    customer_rows = customers_payload.get("customers", [])
    selected_id = render_customer_table(customer_rows)
    if selected_id:
        st.session_state["selected_customer_id"] = selected_id
    elif st.session_state.get("selected_customer_id"):
        selected_id = st.session_state["selected_customer_id"]

    st.divider()

    # Section 3: Customer Detail
    active_id = selected_id or st.session_state.get("selected_customer_id")
    selected_customer: dict | None = None
    if active_id:
        try:
            detail_payload = fetch_detail(active_id)
            render_degraded_banner(detail_payload)
            selected_customer = detail_payload.get("customer") or None
            render_customer_detail(selected_customer or {})
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Could not load customer detail: {exc}")
    else:
        st.info("Select a company from the table to view profile, AI explanation, and recommended actions.")

    st.divider()

    # Section 4: Trends
    try:
        trends_payload = fetch_trends()
        render_degraded_banner(trends_payload)
        render_trends(trends_payload.get("trends", {}))
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Trends unavailable: {exc}")

    st.divider()

    # Section 5: AI Insight Feed
    try:
        feed_payload = fetch_insights()
        render_degraded_banner(feed_payload)
        render_insight_feed(feed_payload.get("items", []))
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Insight feed unavailable: {exc}")

    context_payload = build_analysis_context(
        executive_summary=customers_payload.get("executive_summary"),
        customer_rows=customer_rows,
        active_customer_id=active_id,
        selected_customer=selected_customer,
    )
    render_sidebar(context_payload)


if __name__ == "__main__":
    main()
