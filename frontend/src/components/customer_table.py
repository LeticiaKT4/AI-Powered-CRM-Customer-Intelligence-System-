"""Customer table with search, filter, and sort (PDF section 2)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

STATUS_COLORS = {
    "Healthy": "🟢",
    "At Risk": "🔴",
    "Upsell": "🟡",
}


def render_customer_filters() -> dict:
    col_search, col_filter, col_sort = st.columns([3, 2, 2])
    with col_search:
        search = st.text_input("Search companies", placeholder="Company or industry...", key="cust_search")
    with col_filter:
        at_risk_only = st.checkbox("Show only At Risk", key="cust_at_risk_filter")
    with col_sort:
        sort_by_risk = st.checkbox("Sort by risk (high first)", value=True, key="cust_sort_risk")

    return {
        "search": search.strip() or None,
        "status": "At Risk" if at_risk_only else None,
        "sort_by": "risk_score" if sort_by_risk else "company_name",
        "sort_dir": "desc" if sort_by_risk else "asc",
    }


def render_customer_table(customers: list[dict]) -> str | None:
    """Render customer dataframe; return selected customer_id if any."""
    if not customers:
        st.info("No customers match your filters.")
        return None

    rows = []
    for c in customers:
        status = c.get("status", "")
        rows.append(
            {
                "Company Name": c.get("company_name"),
                "Industry": c.get("industry"),
                "Status": f"{STATUS_COLORS.get(status, '')} {status}",
                "Risk Score": c.get("risk_score"),
                "Confidence": c.get("confidence"),
                "_id": c.get("customer_id"),
            }
        )

    df = pd.DataFrame(rows)
    display_df = df.drop(columns=["_id"])

    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="customer_table_df",
    )

    selected_id: str | None = None
    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        selected_id = str(df.iloc[idx]["_id"])

    names = [c["company_name"] for c in customers]
    pick = st.selectbox("Or select a company", options=[""] + names, key="cust_pick")
    if pick:
        for c in customers:
            if c["company_name"] == pick:
                selected_id = c["customer_id"]
                break

    return selected_id
