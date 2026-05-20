"""HTTP client for the FastAPI backend."""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BACKEND = "http://127.0.0.1:8000"
TIMEOUT = 12.0


def backend_url() -> str:
    return os.getenv("BACKEND_URL", DEFAULT_BACKEND).rstrip("/")


def get_health() -> dict[str, Any]:
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(f"{backend_url()}/api/v1/health")
        r.raise_for_status()
        return r.json()


def get_metrics(keys: str | None = None) -> dict[str, Any]:
    params = {"keys": keys} if keys else None
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(f"{backend_url()}/api/v1/metrics", params=params)
        r.raise_for_status()
        return r.json()


def get_records(
    object_name: str,
    page: int = 1,
    page_size: int = 50,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> dict[str, Any]:
    params: dict[str, Any] = {"page": page, "page_size": page_size, "sort_dir": sort_dir}
    if sort_by:
        params["sort_by"] = sort_by
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(f"{backend_url()}/api/v1/records/{object_name}", params=params)
        r.raise_for_status()
        return r.json()


def get_customers(
    status: str | None = None,
    search: str | None = None,
    sort_by: str = "risk_score",
    sort_dir: str = "desc",
) -> dict[str, Any]:
    params: dict[str, Any] = {"sort_by": sort_by, "sort_dir": sort_dir}
    if status:
        params["status"] = status
    if search:
        params["search"] = search
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(f"{backend_url()}/api/v1/customers", params=params)
        r.raise_for_status()
        return r.json()


def get_customer_detail(customer_id: str) -> dict[str, Any]:
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(f"{backend_url()}/api/v1/customers/{customer_id}")
        r.raise_for_status()
        return r.json()


def get_customer_trends() -> dict[str, Any]:
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(f"{backend_url()}/api/v1/customers/trends")
        r.raise_for_status()
        return r.json()


def get_customer_insights() -> dict[str, Any]:
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(f"{backend_url()}/api/v1/customers/insights")
        r.raise_for_status()
        return r.json()


def post_analysis(body: dict[str, Any]) -> dict[str, Any]:
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.post(f"{backend_url()}/api/v1/analysis", json=body)
        if r.status_code == 408:
            detail = r.json()
            return {"status": "timeout", "detail": detail.get("detail", detail)}
        r.raise_for_status()
        return r.json()
