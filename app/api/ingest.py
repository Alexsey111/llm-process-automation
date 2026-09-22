"""API: POST /ingest — точка входа в конвейер."""
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..core.pipeline import ProcessResult, process_text
from ..db.database import get_conn

router = APIRouter()


class IngestRequest(BaseModel):
    case_type: Literal["financial", "insurance"] = "financial"
    text: str = Field(min_length=1, max_length=20000)
    source: str = Field(default="api", max_length=64)


class IngestResponse(BaseModel):
    status: str
    case_type: str
    audit_id: int | None
    result: dict[str, Any] | None = None
    error: str | None = None


@router.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest) -> IngestResponse:
    outcome: ProcessResult = process_text(request.case_type, request.text, request.source)
    if outcome.status == "llm_error" and outcome.audit_id is None:
        raise HTTPException(status_code=503, detail=outcome.error or "LLM unavailable")
    return IngestResponse(
        status=outcome.status,
        case_type=outcome.case_type,
        audit_id=outcome.audit_id,
        result=outcome.result,
        error=outcome.error,
    )


@router.get("/audit")
def audit(limit: int = 50, case_type: str | None = None) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (min(limit, 200),)
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/results")
def results(limit: int = 50, case_type: str | None = None) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM results ORDER BY id DESC LIMIT ?", (min(limit, 200),)
        ).fetchall()
    return [dict(row) for row in rows]