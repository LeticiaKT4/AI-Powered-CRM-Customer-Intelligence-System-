from fastapi import APIRouter, HTTPException, Query

from models.crm import MetricsResponse
from services.crm_aggregate import build_metrics
from services.crm_cache import get_cache

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(
    keys: str | None = Query(default=None, description="Comma-separated metric keys"),
) -> MetricsResponse:
    key_list = [k.strip() for k in keys.split(",") if k.strip()] if keys else None
    cache = get_cache()
    cache_key = f"metrics:{','.join(sorted(key_list or []))}"

    try:
        result = cache.get_or_fetch(cache_key, lambda: build_metrics(key_list))
        return MetricsResponse(
            degraded=result.degraded,
            warning=result.warning,
            cached_at=result.cached_at,
            data_points=result.data,
        )
    except Exception as exc:  # noqa: BLE001
        if not cache.has(cache_key):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "crm_unavailable",
                    "message": "Unable to load CRM benchmark data and no cached data is available",
                },
            ) from exc
        raise
