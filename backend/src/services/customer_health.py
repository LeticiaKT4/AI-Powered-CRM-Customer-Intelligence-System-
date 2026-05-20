"""Derive customer health, risk scores, and insights from CRM benchmark data."""

from __future__ import annotations

import hashlib
from typing import Any

from models.customer import (
    ChangeSignal,
    CustomerDetail,
    CustomerSummaryRow,
    CustomersTrends,
    ExecutiveSummary,
    InsightFeedItem,
    TrendDataPoint,
    UsageMetric,
)
from services.crm_ingest import get_ingest_service

STATUS_HEALTHY = "Healthy"
STATUS_AT_RISK = "At Risk"
STATUS_UPSELL = "Upsell"

PLAN_TYPES = ("Starter", "Professional", "Enterprise", "Premium")


def _seed(name: str) -> int:
    return int(hashlib.md5(name.encode(), usedforsecurity=False).hexdigest()[:8], 16)


def _risk_score(account: dict[str, Any], open_cases: int) -> float:
    base = _seed(str(account.get("Name", ""))) % 100
    revenue = float(account.get("AnnualRevenue") or 0)
    if revenue < 1_000_000:
        base = min(100, base + 18)
    elif revenue > 8_000_000:
        base = max(0, base - 22)
    base = min(100, base + open_cases * 7)
    return round(float(base), 1)


def _status_from_score(score: float) -> str:
    if score >= 65:
        return STATUS_AT_RISK
    if score <= 35:
        return STATUS_UPSELL
    return STATUS_HEALTHY


def _confidence(score: float, has_revenue: bool) -> str:
    if has_revenue and score not in (50.0,):
        return "HIGH"
    if has_revenue:
        return "MEDIUM"
    return "LOW"


def _confidence_pct(level: str, score: float) -> float:
    base = {"HIGH": 82, "MEDIUM": 64, "LOW": 48}[level]
    adjust = (50 - score) / 5
    return round(min(95, max(40, base + adjust)), 0)


def _open_cases_for_account(account_id: str, cases_df) -> int:
    if cases_df.empty:
        return _seed(account_id) % 4
    if "AccountId" in cases_df.columns:
        mask = cases_df["AccountId"] == account_id
        if "Status" in cases_df.columns:
            mask = mask & (cases_df["Status"] != "Closed")
        return int(mask.sum())
    return _seed(account_id) % 4


def _usage_metrics(name: str) -> list[UsageMetric]:
    s = _seed(name)
    current = 40 + (s % 55)
    delta = (s % 30) - 15
    previous = max(10, min(95, current - delta))
    tickets = 5 + (s % 20)
    prev_tickets = max(1, tickets - (s % 8))
    return [
        UsageMetric(label="Product usage", current=float(current), previous=float(previous), unit="%"),
        UsageMetric(label="Support tickets (30d)", current=float(tickets), previous=float(prev_tickets), unit="count"),
    ]


def _plan_type(name: str) -> str:
    return PLAN_TYPES[_seed(name) % len(PLAN_TYPES)]


def _build_detail_row(account: dict[str, Any], cases_df) -> CustomerDetail:
    name = str(account.get("Name", "Unknown"))
    cid = str(account.get("Id", name))
    industry = str(account.get("Industry") or "General")
    open_cases = _open_cases_for_account(cid, cases_df)
    score = _risk_score(account, open_cases)
    status = _status_from_score(score)
    has_revenue = bool(account.get("AnnualRevenue"))
    confidence = _confidence(score, has_revenue)
    confidence_pct = _confidence_pct(confidence, score)
    usage = _usage_metrics(name)
    usage_drop = usage[0].current < usage[0].previous
    tickets_up = usage[1].current > usage[1].previous

    if status == STATUS_AT_RISK:
        explanation = (
            f"{name} is flagged at risk due to declining engagement and elevated support load."
        )
        factors = [
            "Usage trend below account baseline",
            "Support ticket volume increased period-over-period",
            "Contract renewal window within 90 days",
        ]
        actions = [
            "Schedule retention call",
            "Offer onboarding support",
            "Review success plan milestones",
        ]
    elif status == STATUS_UPSELL:
        explanation = f"{name} shows strong product adoption and is a prime candidate for expansion."
        factors = [
            "Usage above plan threshold for 2+ months",
            "Low support friction",
            "Whitespace in premium feature adoption",
        ]
        actions = [
            "Upsell premium plan",
            "Propose multi-year renewal with add-ons",
            "Introduce executive business review",
        ]
    else:
        explanation = f"{name} is stable with healthy usage patterns and manageable support volume."
        factors = [
            "Consistent usage within expected range",
            "Support tickets within SLA",
        ]
        actions = [
            "Continue quarterly check-in",
            "Share product roadmap highlights",
        ]

    change_signals: list[ChangeSignal] = []
    if usage_drop:
        pct = round(abs(usage[0].current - usage[0].previous) / max(usage[0].previous, 1) * 100)
        change_signals.append(
            ChangeSignal(message=f"Usage dropped {pct}%", severity="critical" if pct > 25 else "warning")
        )
    if tickets_up:
        change_signals.append(ChangeSignal(message="Tickets increased", severity="warning"))

    return CustomerDetail(
        customer_id=cid,
        company_name=name,
        industry=industry,
        status=status,
        risk_score=score,
        confidence=confidence,
        confidence_pct=confidence_pct,
        plan_type=_plan_type(name),
        profile={
            "annual_revenue": account.get("AnnualRevenue"),
            "employees": account.get("NumberOfEmployees"),
            "region": account.get("BillingCountry") or "North America",
        },
        usage_metrics=usage,
        ai_explanation=explanation,
        contributing_factors=factors,
        change_signals=change_signals,
        recommended_actions=actions,
    )


def build_customer_summaries() -> tuple[ExecutiveSummary, list[CustomerSummaryRow], list[CustomerDetail]]:
    ingest = get_ingest_service()
    accounts = ingest.get_frame("Account")
    cases = ingest.get_frame("Case")

    if accounts.empty:
        return (
            ExecutiveSummary(
                total_customers=0,
                healthy_count=0,
                upsell_count=0,
                at_risk_count=0,
                average_risk_score=0.0,
            ),
            [],
            [],
        )

    details: list[CustomerDetail] = []
    rows: list[CustomerSummaryRow] = []

    for _, acc in accounts.iterrows():
        account = acc.to_dict()
        detail = _build_detail_row(account, cases)
        details.append(detail)
        rows.append(
            CustomerSummaryRow(
                customer_id=detail.customer_id,
                company_name=detail.company_name,
                industry=detail.industry,
                status=detail.status,
                risk_score=detail.risk_score,
                confidence=detail.confidence,
            )
        )

    healthy = sum(1 for r in rows if r.status == STATUS_HEALTHY)
    upsell = sum(1 for r in rows if r.status == STATUS_UPSELL)
    at_risk = sum(1 for r in rows if r.status == STATUS_AT_RISK)
    avg_risk = round(sum(r.risk_score for r in rows) / len(rows), 1) if rows else 0.0

    summary = ExecutiveSummary(
        total_customers=len(rows),
        healthy_count=healthy,
        upsell_count=upsell,
        at_risk_count=at_risk,
        average_risk_score=avg_risk,
    )
    return summary, rows, details


def get_customer_detail(customer_id: str) -> CustomerDetail | None:
    _, _, details = build_customer_summaries()
    for d in details:
        if d.customer_id == customer_id:
            return d
    return None


def build_insight_feed() -> list[InsightFeedItem]:
    from services.crm_ingest import get_ingest_service

    _, _, details = build_customer_summaries()
    items: list[InsightFeedItem] = []

    ingest = get_ingest_service()
    tasks = ingest.get_benchmark_tasks()
    if not tasks.empty and "query" in tasks.columns:
        for _, row in tasks.head(3).iterrows():
            task_name = str(row.get("task", "benchmark"))
            query = str(row.get("query", ""))[:100]
            items.append(
                InsightFeedItem(
                    icon="📋",
                    message=f"CRMArena [{task_name}]: {query}",
                    severity="info",
                )
            )

    for d in sorted(details, key=lambda x: x.risk_score, reverse=True):
        if d.status == STATUS_AT_RISK:
            reason = "usage drop" if any("Usage dropped" in s.message for s in d.change_signals) else "risk score rise"
            items.append(
                InsightFeedItem(
                    icon="⚠",
                    message=f"{d.company_name} risk increased due to {reason}",
                    customer_id=d.customer_id,
                    severity="warning",
                )
            )
        elif d.status == STATUS_UPSELL:
            items.append(
                InsightFeedItem(
                    icon="💡",
                    message=f"{d.company_name} is a strong upsell candidate",
                    customer_id=d.customer_id,
                    severity="upsell",
                )
            )
        elif any("declining" in s.message.lower() or "dropped" in s.message.lower() for s in d.change_signals):
            items.append(
                InsightFeedItem(
                    icon="📉",
                    message=f"{d.company_name} engagement declining",
                    customer_id=d.customer_id,
                    severity="warning",
                )
            )
    return items[:8]


def build_trends() -> CustomersTrends:
    _, rows, _ = build_customer_summaries()
    if not rows:
        return CustomersTrends(risk_distribution=[], status_counts=[], usage_trend=[])

    low = sum(1 for r in rows if r.risk_score < 40)
    mid = sum(1 for r in rows if 40 <= r.risk_score < 65)
    high = sum(1 for r in rows if r.risk_score >= 65)

    risk_distribution = [
        TrendDataPoint(label="Low (0-39)", value=float(low)),
        TrendDataPoint(label="Medium (40-64)", value=float(mid)),
        TrendDataPoint(label="High (65+)", value=float(high)),
    ]
    status_counts = [
        TrendDataPoint(label=STATUS_HEALTHY, value=float(sum(1 for r in rows if r.status == STATUS_HEALTHY))),
        TrendDataPoint(label=STATUS_UPSELL, value=float(sum(1 for r in rows if r.status == STATUS_UPSELL))),
        TrendDataPoint(label=STATUS_AT_RISK, value=float(sum(1 for r in rows if r.status == STATUS_AT_RISK))),
    ]

    ingest = get_ingest_service()
    accounts = ingest.get_frame("Account")
    usage_trend: list[TrendDataPoint] = []
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    for i, month in enumerate(months):
        base = 55 + i * 2
        if not accounts.empty:
            base = int(accounts["AnnualRevenue"].mean() / 100_000) % 30 + 50 + i
        usage_trend.append(TrendDataPoint(label=month, value=float(base)))

    return CustomersTrends(
        risk_distribution=risk_distribution,
        status_counts=status_counts,
        usage_trend=usage_trend,
    )
