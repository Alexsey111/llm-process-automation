"""Журнал обработки (audit trail): каждая запись = вход + выход/ошибка + статус."""
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from ..db.database import get_conn

STATUSES = ("success", "escalated", "validation_error", "llm_error")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_audit(
    case_type: str,
    source: str,
    input_text: str,
    status: str,
    llm_raw_output: str | None = None,
    validated_output: dict[str, Any] | None = None,
    confidence: str | None = None,
    escalate: bool | None = None,
    error: str | None = None,
    result_json: dict[str, Any] | None = None,
) -> int:
    """Пишет запись в audit_log (и results, если есть валидный результат). Возвращает audit_id."""
    if status not in STATUSES:
        raise ValueError(f"Unknown audit status: {status}")

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO audit_log
                (case_type, source, created_at, input_text, llm_raw_output,
                 validated_output, status, confidence, escalate, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_type,
                source,
                _now(),
                input_text,
                llm_raw_output,
                json.dumps(validated_output, ensure_ascii=False) if validated_output else None,
                status,
                confidence,
                int(escalate) if escalate is not None else None,
                error,
            ),
        )
        audit_id = int(cursor.lastrowid)

        if result_json is not None:
            conn.execute(
                """
                INSERT INTO results (audit_id, case_type, created_at, status, result_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (audit_id, case_type, _now(), status, json.dumps(result_json, ensure_ascii=False)),
            )

    return audit_id


def list_audit(limit: int = 50, case_type: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM audit_log"
    params: list[Any] = []
    if case_type:
        query += " WHERE case_type = ?"
        params.append(case_type)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def list_results(limit: int = 50, case_type: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM results"
    params: list[Any] = []
    if case_type:
        query += " WHERE case_type = ?"
        params.append(case_type)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]