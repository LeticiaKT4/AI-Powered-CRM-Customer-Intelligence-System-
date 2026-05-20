import uuid

from fastapi import APIRouter, HTTPException

from models.analysis import AnalysisRequestBody, AnalysisResponse, AnalysisStatus, ContextScope
from services.analysis_context import enrich_analysis_context
from services.gemini_client import (
    AnalysisTimeoutError,
    GeminiServiceError,
    run_analysis,
)

router = APIRouter()


@router.get("/analysis")
def analysis_usage() -> dict:
    """Help browsers and tools that GET this URL by mistake (use POST for real analysis)."""
    return {
        "message": "AI analysis requires POST with a JSON body.",
        "method": "POST",
        "url": "/api/v1/analysis",
        "example_body": {
            "prompt": "Summarize at-risk customers",
            "analysis_type": "summary",
            "context_scope": "dashboard",
            "context_payload": {},
        },
        "docs": "/docs",
    }


@router.post("/analysis", response_model=AnalysisResponse)
def post_analysis(body: AnalysisRequestBody) -> AnalysisResponse:
    enriched = enrich_analysis_context(body.context_payload, prompt=body.prompt)
    scope = body.context_scope
    if enriched.get("selected_customer") or enriched.get("prompt_matched_customer_detail"):
        scope = ContextScope.table_selection
    request = body.model_copy(update={"context_payload": enriched, "context_scope": scope})
    try:
        request_id, result = run_analysis(request)
        return AnalysisResponse(
            request_id=request_id,
            status=AnalysisStatus.completed,
            result=result,
        )
    except AnalysisTimeoutError:
        raise HTTPException(
            status_code=408,
            detail={
                "error": "analysis_timeout",
                "message": "AI analysis exceeded the 10 second limit. Please retry.",
                "request_id": str(uuid.uuid4()),
            },
        ) from None
    except GeminiServiceError as exc:
        status = 429 if exc.error_code == "gemini_quota" else 502
        raise HTTPException(
            status_code=status,
            detail={"error": exc.error_code, "message": str(exc)},
        ) from exc
