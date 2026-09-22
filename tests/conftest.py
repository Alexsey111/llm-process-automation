"""Общие фикстуры: подменяем вызов LLM на детерминированный мок и создаём тестовую БД."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import llm as llm_module  # noqa: E402
from app.core import pipeline as pipeline_module  # noqa: E402


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Каждый тест получает свою пустую БД."""
    from app.core import config as config_module
    from app.db import database as database_module

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(config_module, "DB_PATH", str(db_path))
    monkeypatch.setattr(database_module, "DB_PATH", str(db_path))
    database_module.init_db()
    return db_path


@pytest.fixture
def mock_llm(monkeypatch):
    """Подменяет call_llm_extract; по умолчанию возвращает заглушку, можно задать per-test."""
    store = {"response": {}, "calls": 0}

    def _set(response):
        store["response"] = response

    def _fake_call(system_prompt: str, user_text: str):
        store["calls"] += 1
        if store["calls"] > 1 and not store["response"]:
            # на повторном вызове — исправляемся: валидный JSON
            return dict(store["response"])
        return store["response"]

    monkeypatch.setattr(pipeline_module, "call_llm_extract", _fake_call)
    monkeypatch.setattr(llm_module, "call_llm_extract", _fake_call)
    store["set"] = _set
    return store