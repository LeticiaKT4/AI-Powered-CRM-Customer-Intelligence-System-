"""AI analysis domain models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AnalysisType(str, Enum):
    question = "question"
    prediction = "prediction"
    summary = "summary"


class ContextScope(str, Enum):
    dashboard = "dashboard"
    widget = "widget"
    table_selection = "table_selection"


class AnalysisStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    timeout = "timeout"


class AnalysisRequestBody(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    analysis_type: AnalysisType = AnalysisType.question
    context_scope: ContextScope = ContextScope.dashboard
    context_payload: dict[str, Any] = Field(default_factory=dict)


class StructuredInsights(BaseModel):
    bullets: list[str] = Field(default_factory=list)
    confidence: str = "medium"


class AnalysisResultBody(BaseModel):
    content: str
    structured_insights: StructuredInsights | None = None
    model: str
    latency_ms: int


class AnalysisResponse(BaseModel):
    request_id: str
    status: AnalysisStatus
    result: AnalysisResultBody | None = None
