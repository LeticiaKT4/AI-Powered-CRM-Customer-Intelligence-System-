"""Build context_payload for AI analysis from dashboard state."""

from __future__ import annotations

from typing import Any

MAX_VISIBLE_CUSTOMERS = 50


def build_analysis_context(
    *,
    executive_summary: dict | None,
    customer_rows: list[dict],
    active_customer_id: str | None,
    selected_customer: dict | None,
) -> dict[str, Any]:
    """Package visible dashboard data so the model can answer customer-specific questions."""
    visible = customer_rows[:MAX_VISIBLE_CUSTOMERS]
    payload: dict[str, Any] = {
        "executive_summary": executive_summary or {},
        "customer_count": len(customer_rows),
        "customers_visible": visible,
        "customers_visible_truncated": len(customer_rows) > MAX_VISIBLE_CUSTOMERS,
    }

    if active_customer_id:
        payload["selected_customer_id"] = active_customer_id
    if selected_customer:
        payload["selected_customer"] = selected_customer

    return payload
