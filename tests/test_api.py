"""API-тесты: POST /ingest, GET /audit, GET /results (мок LLM)."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health(mock_llm):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ingest_success(mock_llm):
    mock_llm["set"]({
        "document_type": "invoice", "document_number": "481",
        "document_date": "2026-09-18", "counterparty": "ООО Альфа",
        "amount": 125000.0, "currency": "RUB", "vat_rate": 20,
        "payment_due_date": "2026-09-25", "purpose": "консультационные услуги",
        "confidence": "high", "missing_fields": [],
        "next_action": "approve_payment", "escalate": False,
    })
    r = client.post("/ingest", json={
        "case_type": "financial",
        "text": "Счёт №481 от 18.09.2026, ООО Альфа, 125000 руб., оплата до 25.09.2026.",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["result"]["amount"] == 125000.0
    assert body["audit_id"] is not None


def test_ingest_escalation(mock_llm):
    mock_llm["set"]({
        "claim_type": "transport_damage", "incident_date": "2026-09-18",
        "description": "Повреждение корпуса станка при перевозке",
        "estimated_damage": 180000.0, "currency": "RUB", "policy_number": None,
        "evidence": ["photos"], "required_missing": ["policy_number"],
        "confidence": "medium", "next_action": "request_missing_information",
        "escalate": True,
    })
    r = client.post("/ingest", json={
        "case_type": "insurance",
        "text": "Повреждение станка при перевозке 18.09.2026, ущерб 180000 руб., полиса нет.",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "escalated"
    assert "policy_number" in body["result"]["required_missing"]


def test_ingest_invalid_body_rejected(mock_llm):
    r = client.post("/ingest", json={"case_type": "medical", "text": "тест"})
    assert r.status_code == 422


def test_audit_endpoint(mock_llm):
    mock_llm["set"]({
        "document_type": "invoice", "document_number": "1", "document_date": "2026-01-01",
        "counterparty": "X", "amount": 1.0, "currency": "RUB", "vat_rate": None,
        "payment_due_date": None, "purpose": None, "confidence": "high",
        "missing_fields": [], "next_action": "approve_payment", "escalate": False,
    })
    client.post("/ingest", json={"case_type": "financial", "text": "Счёт №1 от X, сумма 1 руб."})
    r = client.get("/audit")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    assert rows[0]["case_type"] == "financial"


def test_results_endpoint(mock_llm):
    mock_llm["set"]({
        "document_type": "invoice", "document_number": "2", "document_date": None,
        "counterparty": "Y", "amount": 5.0, "currency": "RUB", "vat_rate": None,
        "payment_due_date": None, "purpose": None, "confidence": "high",
        "missing_fields": [], "next_action": "approve_payment", "escalate": False,
    })
    client.post("/ingest", json={"case_type": "financial", "text": "Счёт №2 от Y, сумма 5 руб."})
    r = client.get("/results")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    assert "result_json" in rows[0]