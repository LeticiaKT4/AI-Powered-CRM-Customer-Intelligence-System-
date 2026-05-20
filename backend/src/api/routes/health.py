from fastapi import APIRouter

from config import get_settings
from services.crm_ingest import get_ingest_service

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str | bool | int | dict[str, int]]:
    settings = get_settings()
    ingest = get_ingest_service()
    return {
        "status": "ok",
        "crm_data_mode": settings.crm_data_mode,
        "data_source": ingest.data_source,
        "record_counts": ingest.record_counts,
        "benchmark_tasks": len(ingest.get_benchmark_tasks()),
        "gemini_configured": bool(settings.gemini_api_key.strip()),
        "gemini_model": settings.gemini_model,
    }
