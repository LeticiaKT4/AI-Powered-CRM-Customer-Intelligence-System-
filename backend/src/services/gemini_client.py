"""Google Gemini API client with 10s timeout (FR-009, FR-012)."""

from __future__ import annotations

import json
import logging
import re
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

# Fallback models if the configured model is unavailable for this API key.
_MODEL_FALLBACKS = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
)


class AnalysisTimeoutError(Exception):
    """Raised when analysis exceeds configured timeout."""


class GeminiServiceError(Exception):
    """Raised when Gemini API fails."""

    def __init__(self, message: str, *, error_code: str = "gemini_error") -> None:
        super().__init__(message)
        self.error_code = error_code


def _truncate_context(payload: dict) -> dict:
    encoded = json.dumps(payload, default=str).encode("utf-8")
    if len(encoded) <= MAX_CONTEXT_BYTES:
        return payload
    return {"truncated": True, "summary": encoded[:MAX_CONTEXT_BYTES].decode("utf-8", errors="ignore")}


def build_prompt(request: AnalysisRequestBody) -> str:
    context = _truncate_context(request.context_payload)
    return (
        "You are a CRM customer health analyst. Answer ONLY using the JSON data below.\n"
        f"Analysis type: {request.analysis_type.value}\n"
        f"Context scope: {request.context_scope.value}\n\n"
        "How to use the context:\n"
        "- `selected_customer`: the account the user selected in the UI (primary focus).\n"
        "- `prompt_matched_customer` / `prompt_matched_customer_detail`: row/detail when the "
        "user names a company in their question.\n"
        "- `customers_visible`: portfolio rows with company_name, status, risk_score, confidence.\n"
        "- `executive_summary`: portfolio-level KPIs.\n"
        "Match user questions to company_name (and customer_id). Do not claim data is missing "
        "if the answer appears in this JSON.\n\n"
        f"Data context (JSON):\n{json.dumps(context, default=str, indent=2)}\n\n"
        f"User question: {request.prompt.strip()}\n\n"
        "Respond with concise markdown. Include actionable insights."
    )


def _normalize_model(name: str) -> str:
    name = name.strip()
    if name.startswith("models/"):
        return name[len("models/") :]
    return name


def _format_gemini_error(exc: Exception) -> GeminiServiceError:
    raw = str(exc)
    logger.warning("Gemini API call failed: %s", raw)

    if re.search(r"429|RESOURCE_EXHAUSTED|quota", raw, re.I):
        return GeminiServiceError(
            "Gemini API quota exceeded for this key. Check usage and billing at "
            "https://ai.google.dev/gemini-api/docs/rate-limits — or wait and retry later.",
            error_code="gemini_quota",
        )
    if re.search(r"403|API_KEY_INVALID|PERMISSION_DENIED|invalid.*api.*key", raw, re.I):
        return GeminiServiceError(
            "Gemini API key is invalid or not permitted. Create or fix your key at "
            "https://aistudio.google.com/apikey (use an unrestricted key for server apps).",
            error_code="gemini_auth",
        )
    if re.search(r"404|NOT_FOUND|model.*not", raw, re.I):
        return GeminiServiceError(
            f"Gemini model not found ({get_settings().gemini_model}). "
            "Set GEMINI_MODEL to a supported value such as gemini-2.5-flash in .env.",
            error_code="gemini_model",
        )
    return GeminiServiceError(raw[:500] or "Gemini API request failed.", error_code="gemini_error")


def _extract_text(response) -> str:
    text = getattr(response, "text", None) or ""
    if text:
        return text
    candidates = getattr(response, "candidates", None) or []
    if candidates:
        parts = candidates[0].content.parts
        text = "".join(getattr(p, "text", "") for p in parts)
    return text or "No content returned from model."


def _generate_with_model(client, model: str, prompt: str):
    return client.models.generate_content(model=model, contents=prompt)


def _call_gemini(prompt: str) -> str:
    settings = get_settings()
    if not settings.gemini_api_key:
        return (
            "## Demo analysis (no GEMINI_API_KEY configured)\n\n"
            "- Set `GEMINI_API_KEY` in the project root `.env` file and restart the API server.\n"
            "- At-risk accounts show declining usage; prioritize retention outreach.\n"
            "- Upsell candidates have strong adoption — consider premium plan conversations.\n"
        )

    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key)
    primary = _normalize_model(settings.gemini_model)
    models_to_try = [primary, *[m for m in _MODEL_FALLBACKS if m != primary]]

    last_error: GeminiServiceError | None = None
    for model in models_to_try:
        try:
            response = _generate_with_model(client, model, prompt)
            return _extract_text(response)
        except Exception as exc:  # noqa: BLE001
            formatted = _format_gemini_error(exc)
            # Quota/auth errors won't be fixed by switching models.
            if formatted.error_code in ("gemini_quota", "gemini_auth"):
                raise formatted from exc
            last_error = formatted
            logger.info("Model %s failed, trying next fallback if any", model)

    if last_error:
        raise last_error
    raise GeminiServiceError("Gemini API request failed with no available model.")


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
        except GeminiServiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _format_gemini_error(exc) from exc

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
