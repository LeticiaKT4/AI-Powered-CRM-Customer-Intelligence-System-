import uuid

from fastapi import APIRouter, HTTPException

from models.analysis import AnalysisRequestBody, AnalysisResponse, AnalysisStatus
from services.gemini_client import (
    AnalysisTimeoutError,
    GeminiServiceError,
    run_analysis,
)

router = APIRouter()


@router.post("/analysis", response_model=AnalysisResponse)
def post_analysis(body: AnalysisRequestBody) -> AnalysisResponse:
    try:
        request_id, result = run_analysis(body)
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
        raise HTTPException(
            status_code=502,
            detail={"error": "gemini_error", "message": str(exc)},
        ) from exc
