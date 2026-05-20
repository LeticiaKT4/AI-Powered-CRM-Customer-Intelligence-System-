"""Customer health dashboard API."""

from fastapi import APIRouter, HTTPException, Query

from models.customer import (
    CustomerDetailResponse,
    CustomersListResponse,
    CustomersTrendsResponse,
    InsightFeedResponse,
)
from services.crm_cache import get_cache
from services.customer_health import (
    build_customer_summaries,
    build_insight_feed,
    build_trends,
    get_customer_detail,
)

router = APIRouter()


def _fetch_summaries():
    summary, rows, _ = build_customer_summaries()
    return summary, rows


@router.get("/customers", response_model=CustomersListResponse)
def list_customers(
    status: str | None = Query(default=None, description="Filter by status"),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="risk_score"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> CustomersListResponse:
    cache = get_cache()
    cache_key = f"customers:list:{status}:{search}:{sort_by}:{sort_dir}"

    def fetch():
        return _fetch_summaries()

    try:
        result = cache.get_or_fetch(cache_key, fetch)
        summary, rows = result.data
    except Exception as exc:  # noqa: BLE001
        if not cache.has(cache_key):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "crm_unavailable",
                    "message": "Unable to load customer health data",
                },
            ) from exc
        raise

    if status:
        rows = [r for r in rows if r.status.lower() == status.lower().replace("_", " ")]
    if search:
        q = search.lower()
        rows = [r for r in rows if q in r.company_name.lower() or q in r.industry.lower()]

    reverse = sort_dir == "desc"
    if sort_by == "company_name":
        rows = sorted(rows, key=lambda r: r.company_name.lower(), reverse=reverse)
    elif sort_by == "risk_score":
        rows = sorted(rows, key=lambda r: r.risk_score, reverse=reverse)
    else:
        rows = sorted(rows, key=lambda r: r.status, reverse=reverse)

    return CustomersListResponse(
        degraded=result.degraded,
        warning=result.warning,
        cached_at=result.cached_at,
        executive_summary=summary,
        customers=rows,
    )


@router.get("/customers/trends", response_model=CustomersTrendsResponse)
def customer_trends() -> CustomersTrendsResponse:
    cache = get_cache()
    cache_key = "customers:trends"

    try:
        result = cache.get_or_fetch(cache_key, build_trends)
        return CustomersTrendsResponse(
            degraded=result.degraded,
            warning=result.warning,
            cached_at=result.cached_at,
            trends=result.data,
        )
    except Exception as exc:  # noqa: BLE001
        if not cache.has(cache_key):
            raise HTTPException(status_code=503, detail={"error": "crm_unavailable"}) from exc
        raise


@router.get("/customers/insights", response_model=InsightFeedResponse)
def customer_insights() -> InsightFeedResponse:
    cache = get_cache()
    cache_key = "customers:insights"

    try:
        result = cache.get_or_fetch(cache_key, build_insight_feed)
        return InsightFeedResponse(
            degraded=result.degraded,
            warning=result.warning,
            cached_at=result.cached_at,
            items=result.data,
        )
    except Exception as exc:  # noqa: BLE001
        if not cache.has(cache_key):
            raise HTTPException(status_code=503, detail={"error": "crm_unavailable"}) from exc
        raise


@router.get("/customers/{customer_id}", response_model=CustomerDetailResponse)
def customer_detail(customer_id: str) -> CustomerDetailResponse:
    cache = get_cache()
    cache_key = f"customers:detail:{customer_id}"

    def fetch():
        detail = get_customer_detail(customer_id)
        if detail is None:
            raise ValueError("not_found")
        return detail

    try:
        result = cache.get_or_fetch(cache_key, fetch)
        return CustomerDetailResponse(
            degraded=result.degraded,
            warning=result.warning,
            cached_at=result.cached_at,
            customer=result.data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Customer not found"}) from exc
    except Exception as exc:  # noqa: BLE001
        if not cache.has(cache_key):
            raise HTTPException(status_code=503, detail={"error": "crm_unavailable"}) from exc
        raise
