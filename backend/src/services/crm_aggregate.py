"""Aggregate CRM DataFrames into metrics and paginated record sets."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from config import get_settings
from models.crm import CRMDataPoint
from services.crm_ingest import get_ingest_service

logger = logging.getLogger(__name__)

# Malformed rows: skip rows missing required keys; log count (T044 / spec edge case).


def _safe_rows(df: pd.DataFrame, required: list[str]) -> tuple[pd.DataFrame, int]:
    if df.empty:
        return df, 0
    mask = df[required].notna().all(axis=1) if all(c in df.columns for c in required) else pd.Series([True] * len(df))
    skipped = int((~mask).sum())
    if skipped:
        logger.info("Skipped %s malformed rows (missing %s)", skipped, required)
    return df[mask].copy(), skipped


def build_metrics(keys: list[str] | None = None) -> list[CRMDataPoint]:
    ingest = get_ingest_service()
    points: list[CRMDataPoint] = []
    now = datetime.now(timezone.utc)

    opp = ingest.get_frame("Opportunity")
    opp, _ = _safe_rows(opp, ["StageName", "Amount"]) if not opp.empty else (opp, 0)

    if opp is not None and not opp.empty and (keys is None or "pipeline_by_stage" in keys):
        grouped = opp.groupby("StageName", dropna=True)["Amount"].sum()
        for stage, amount in grouped.items():
            points.append(
                CRMDataPoint(
                    id=str(uuid.uuid4()),
                    metric_key="pipeline_by_stage",
                    label=str(stage),
                    value=float(amount),
                    unit="USD",
                    timestamp=now,
                    dimensions={"stage": str(stage)},
                    source_object="Opportunity",
                )
            )
        points.append(
            CRMDataPoint(
                id=str(uuid.uuid4()),
                metric_key="opportunity_pipeline_total",
                label="Pipeline Total",
                value=float(opp["Amount"].sum()),
                unit="USD",
                timestamp=now,
                source_object="Opportunity",
            )
        )

    accounts = ingest.get_frame("Account")
    if not accounts.empty and (keys is None or "account_count" in keys):
        points.append(
            CRMDataPoint(
                id=str(uuid.uuid4()),
                metric_key="account_count",
                label="Total Accounts",
                value=len(accounts),
                unit="count",
                timestamp=now,
                source_object="Account",
            )
        )

    if keys:
        points = [p for p in points if p.metric_key in keys]
    return points


def paginate_records(
    object_name: str,
    page: int = 1,
    page_size: int = 50,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> tuple[list[str], list[dict[str, Any]], int]:
    settings = get_settings()
    page_size = min(max(1, page_size), settings.max_page_size)
    page = max(1, page)

    df = get_ingest_service().get_frame(object_name)
    if df.empty:
        return [], [], 0

    if sort_by and sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=(sort_dir == "asc"))

    total = len(df)
    start = (page - 1) * page_size
    end = start + page_size
    page_df = df.iloc[start:end]
    columns = list(page_df.columns)
    rows = page_df.to_dict(orient="records")
    return columns, rows, total
