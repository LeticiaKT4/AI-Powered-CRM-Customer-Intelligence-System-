"""Google Gemini API client with 10s timeout (FR-009, FR-012)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from config import get_settings
from models.analysis import (
    AnalysisRequestBody,
    AnalysisResultBody,
    AnalysisStatus,
    StructuredInsights,
)

logger = logging.getLogger(__name__)

MAX_CONTEXT_BYTES = 32 * 1024


class AnalysisTimeoutError(Exception):
    """Raised when analysis exceeds configured timeout."""


class GeminiServiceError(Exception):
    """Raised when Gemini API fails."""


def _truncate_context(payload: dict) -> dict:
    encoded = json.dumps(payload, default=str).encode("utf-8")
    if len(encoded) <= MAX_CONTEXT_BYTES:
        return payload
    return {"truncated": True, "summary": encoded[:MAX_CONTEXT_BYTES].decode("utf-8", errors="ignore")}


def build_prompt(request: AnalysisRequestBody) -> str:
    context = _truncate_context(request.context_payload)
    return (
        f"You are a CRM analytics assistant.\n"
        f"Analysis type: {request.analysis_type.value}\n"
        f"Context scope: {request.context_scope.value}\n"
        f"Data context (JSON): {json.dumps(context, default=str)}\n\n"
        f"User question: {request.prompt.strip()}\n\n"
        "Respond with concise markdown. Include actionable insights."
    )


def _call_gemini(prompt: str) -> str:
    settings = get_settings()
    if not settings.gemini_api_key:
        return (
            "## Demo analysis (no GEMINI_API_KEY configured)\n\n"
            "- Pipeline is concentrated in **Negotiation** and **Prospecting** stages.\n"
            "- Consider prioritizing high-value opportunities in Negotiation.\n"
            "- Lead volume is modest; focus on conversion from Open leads.\n"
        )

    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(model=settings.gemini_model, contents=prompt)
    text = getattr(response, "text", None) or ""
    if not text and hasattr(response, "candidates") and response.candidates:
        parts = response.candidates[0].content.parts
        text = "".join(getattr(p, "text", "") for p in parts)
    return text or "No content returned from model."


def run_analysis(request: AnalysisRequestBody) -> tuple[str, AnalysisResultBody]:
    settings = get_settings()
    prompt = build_prompt(request)
    request_id = str(uuid.uuid4())
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_call_gemini, prompt)
        try:
            content = future.result(timeout=settings.analysis_timeout_seconds)
        except FuturesTimeoutError as exc:
            raise AnalysisTimeoutError("AI analysis exceeded the 10 second limit") from exc
        except Exception as exc:  # noqa: BLE001
            raise GeminiServiceError(str(exc)) from exc

    latency_ms = int((time.perf_counter() - start) * 1000)
    result = AnalysisResultBody(
        content=content,
        structured_insights=StructuredInsights(
            bullets=[line.lstrip("- ").strip() for line in content.splitlines() if line.strip().startswith("-")][:5],
            confidence="medium",
        ),
        model=settings.gemini_model,
        latency_ms=latency_ms,
    )
    return request_id, result
