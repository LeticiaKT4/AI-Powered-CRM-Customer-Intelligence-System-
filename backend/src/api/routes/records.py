from fastapi import APIRouter, HTTPException, Query

from models.crm import RecordsResponse
from services.crm_aggregate import paginate_records
from services.crm_cache import get_cache

router = APIRouter()


@router.get("/records/{object_name}", response_model=RecordsResponse)
def get_records(
    object_name: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: str | None = None,
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> RecordsResponse:
    cache = get_cache()
    cache_key = f"records:{object_name}:{page}:{page_size}:{sort_by}:{sort_dir}"

    def fetch() -> tuple:
        return paginate_records(object_name, page, page_size, sort_by, sort_dir)

    try:
        result = cache.get_or_fetch(cache_key, fetch)
        columns, rows, total = result.data
        return RecordsResponse(
            degraded=result.degraded,
            warning=result.warning,
            cached_at=result.cached_at,
            object_name=object_name,
            page=page,
            page_size=page_size,
            total=total,
            columns=columns,
            rows=rows,
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
