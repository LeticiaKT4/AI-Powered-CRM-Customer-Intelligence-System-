"""CRM domain models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CRMDataPoint(BaseModel):
    id: str
    metric_key: str
    label: str
    value: float | str
    unit: str | None = None
    timestamp: datetime | None = None
    dimensions: dict[str, Any] = Field(default_factory=dict)
    source_object: str | None = None


class MetricsResponse(BaseModel):
    degraded: bool = False
    warning: str | None = None
    cached_at: datetime | None = None
    data_points: list[CRMDataPoint] = Field(default_factory=list)


class RecordsResponse(BaseModel):
    degraded: bool = False
    warning: str | None = None
    cached_at: datetime | None = None
    object_name: str
    page: int
    page_size: int
    total: int
    columns: list[str]
    rows: list[dict[str, Any]]
