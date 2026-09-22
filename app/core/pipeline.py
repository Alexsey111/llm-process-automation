"""Общий конвейер обработки: вход -> LLM -> schema validation -> business rules -> audit.

Возвращает ProcessResult: LLM не является источником истины — финальное решение
об эскалации принимает детерминированный Python-код.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from ..cases.registry import CaseConfig, get_case
from .audit import write_audit
from .llm import LLMError, call_llm_extract
from .validation import validate_schema

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    case_type: str
    status: str  # success | escalated | validation_error | llm_error
    result: dict[str, Any] | None = None
    audit_id: int | None = None
    error: str | None = None
    llm_raw: str | None = None
    notes: list[str] = field(default_factory=list)


def process_text(case_type: str, text: str, source: str = "api") -> ProcessResult:
    try:
        case: CaseConfig = get_case(case_type)
    except KeyError as exc:
        return ProcessResult(case_type=case_type, status="llm_error", error=str(exc))

    text = text.strip()
    if not text:
        error = "Input text is empty"
        audit_id = write_audit(
            case_type=case_type, source=source, input_text=text,
            status="validation_error", error=error,
        )
        return ProcessResult(case_type=case_type, status="validation_error", error=error, audit_id=audit_id)

    # --- Шаг 1: LLM extraction ---
    try:
        raw_json = call_llm_extract(case.system_prompt, text)
    except LLMError as exc:
        audit_id = write_audit(
            case_type=case_type, source=source, input_text=text,
            status="llm_error", error=str(exc),
        )
        return ProcessResult(case_type=case_type, status="llm_error", error=str(exc), audit_id=audit_id)

    llm_raw = json.dumps(raw_json, ensure_ascii=False)

    # --- Шаг 2: schema validation (Pydantic) ---
    validated, validation_error = validate_schema(case.schema, raw_json)
    if validation_error:
        audit_id = write_audit(
            case_type=case_type, source=source, input_text=text,
            status="validation_error", llm_raw_output=llm_raw,
            error=validation_error,
        )
        return ProcessResult(
            case_type=case_type, status="validation_error",
            error=validation_error, llm_raw=llm_raw, audit_id=audit_id,
        )

    # --- Шаг 3: deterministic business rules (escalation) ---
    result = case.apply_rules(validated)
    result_dict = case.to_dict(result)
    escalate = bool(result_dict.get("escalate"))
    status = "escalated" if escalate else "success"

    # --- Шаг 4: audit + result ---
    audit_id = write_audit(
        case_type=case_type, source=source, input_text=text,
        status=status, llm_raw_output=llm_raw, validated_output=result_dict,
        confidence=result_dict.get("confidence"), escalate=escalate,
        result_json=result_dict,
    )

    return ProcessResult(
        case_type=case_type, status=status, result=result_dict,
        audit_id=audit_id, llm_raw=llm_raw,
    )