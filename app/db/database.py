"""SQLite: схема audit_log + результаты."""
import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from ..core.config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_type TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'api',
    created_at TEXT NOT NULL,
    input_text TEXT NOT NULL,
    llm_raw_output TEXT,
    validated_output TEXT,
    status TEXT NOT NULL,
    confidence TEXT,
    escalate INTEGER,
    error TEXT
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id INTEGER NOT NULL REFERENCES audit_log(id),
    case_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT NOT NULL
);
"""


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.executescript(_SCHEMA)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()