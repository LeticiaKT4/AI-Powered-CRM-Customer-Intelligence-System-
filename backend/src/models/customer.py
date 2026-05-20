"""Customer health dashboard models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

CustomerStatus = Literal["Healthy", "At Risk", "Upsell"]
ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW"]


class CustomerSummaryRow(BaseModel):
    customer_id: str
    company_name: str
    industry: str
    status: CustomerStatus
    risk_score: float
    confidence: ConfidenceLevel


class ExecutiveSummary(BaseModel):
    total_customers: int
    healthy_count: int
    upsell_count: int
    at_risk_count: int
    average_risk_score: float


class UsageMetric(BaseModel):
    label: str
    current: float
    previous: float
    unit: str = "%"


class ChangeSignal(BaseModel):
    message: str
    severity: Literal["info", "warning", "critical"] = "warning"


class CustomerDetail(BaseModel):
    customer_id: str
    company_name: str
    industry: str
    status: CustomerStatus
    risk_score: float
    confidence: ConfidenceLevel
    confidence_pct: float
    plan_type: str
    profile: dict[str, Any] = Field(default_factory=dict)
    usage_metrics: list[UsageMetric] = Field(default_factory=list)
    ai_explanation: str
    contributing_factors: list[str] = Field(default_factory=list)
    change_signals: list[ChangeSignal] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class InsightFeedItem(BaseModel):
    icon: str
    message: str
    customer_id: str | None = None
    severity: Literal["info", "warning", "upsell"] = "info"


class TrendDataPoint(BaseModel):
    label: str
    value: float


class CustomersTrends(BaseModel):
    risk_distribution: list[TrendDataPoint]
    status_counts: list[TrendDataPoint]
    usage_trend: list[TrendDataPoint]


class CustomersListResponse(BaseModel):
    degraded: bool = False
    warning: str | None = None
    cached_at: datetime | None = None
    executive_summary: ExecutiveSummary
    customers: list[CustomerSummaryRow]


class CustomerDetailResponse(BaseModel):
    degraded: bool = False
    warning: str | None = None
    cached_at: datetime | None = None
    customer: CustomerDetail


class InsightFeedResponse(BaseModel):
    degraded: bool = False
    warning: str | None = None
    cached_at: datetime | None = None
    items: list[InsightFeedItem]


class CustomersTrendsResponse(BaseModel):
    degraded: bool = False
    warning: str | None = None
    cached_at: datetime | None = None
    trends: CustomersTrends
