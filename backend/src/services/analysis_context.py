"""Enrich AI analysis context with customer records the model can reason over."""

from __future__ import annotations

import re
from typing import Any

from services.customer_health import build_customer_summaries, get_customer_detail

MAX_VISIBLE_CUSTOMERS = 50


def _row_to_dict(row: Any) -> dict[str, Any]:
    if hasattr(row, "model_dump"):
        return row.model_dump()
    if isinstance(row, dict):
        return row
    return dict(row)


def _detail_to_dict(detail: Any) -> dict[str, Any] | None:
    if detail is None:
        return None
    if hasattr(detail, "model_dump"):
        return detail.model_dump()
    if isinstance(detail, dict):
        return detail
    return None


def _name_tokens(name: str) -> list[str]:
    return [t.lower() for t in re.split(r"[\s,.-]+", name) if len(t) > 2]


def _prompt_mentions_customer(prompt: str, company_name: str) -> bool:
    prompt_l = prompt.lower()
    name_l = company_name.lower()
    if name_l in prompt_l:
        return True
    tokens = _name_tokens(company_name)
    if len(tokens) >= 2 and all(t in prompt_l for t in tokens):
        return True
    # Match "First Last" style names in prompt against company or person-like tokens
    if len(tokens) == 1 and tokens[0] in prompt_l:
        return True
    return False


def _find_customer_in_visible(
    prompt: str, visible: list[dict[str, Any]]
) -> dict[str, Any] | None:
    for row in visible:
        name = row.get("company_name") or ""
        if name and _prompt_mentions_customer(prompt, name):
            return row
    return None


def enrich_analysis_context(
    context_payload: dict[str, Any],
    prompt: str = "",
) -> dict[str, Any]:
    """
    Ensure context_payload includes enough CRM facts for Gemini to answer
    customer-specific and name-based questions.
    """
    payload = dict(context_payload)

    visible = payload.get("customers_visible")
    if not visible:
        _, rows, _ = build_customer_summaries()
        payload["customers_visible"] = [_row_to_dict(r) for r in rows[:MAX_VISIBLE_CUSTOMERS]]
        payload["customers_visible_truncated"] = len(rows) > MAX_VISIBLE_CUSTOMERS
    elif len(visible) > MAX_VISIBLE_CUSTOMERS:
        payload["customers_visible"] = visible[:MAX_VISIBLE_CUSTOMERS]
        payload["customers_visible_truncated"] = True

    visible = payload.get("customers_visible") or []

    selected = payload.get("selected_customer")
    selected_id = payload.get("selected_customer_id")

    if not selected and selected_id:
        detail = get_customer_detail(str(selected_id))
        if detail:
            payload["selected_customer"] = _detail_to_dict(detail)

    selected = payload.get("selected_customer")

    # If the user names a company/person in the prompt, attach matching profile.
    if prompt and visible:
        match_row = _find_customer_in_visible(prompt, visible)
        if match_row:
            payload["prompt_matched_customer"] = match_row
            match_id = match_row.get("customer_id")
            if match_id and (not selected or selected.get("customer_id") != match_id):
                detail = get_customer_detail(str(match_id))
                if detail:
                    payload["prompt_matched_customer_detail"] = _detail_to_dict(detail)

    if selected:
        payload["selected_customer_id"] = selected.get("customer_id") or selected_id

    return payload
