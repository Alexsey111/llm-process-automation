"""Unit-тесты deterministic business-rules кейса F (без LLM)."""
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.cases.financial.rules import apply_rules
from app.cases.financial.schemas import FinancialExtraction


def make(**overrides):
    base = dict(
        document_type="invoice",
        document_number="481",
        document_date="2026-09-18",
        counterparty="ООО Альфа",
        amount=125000.0,
        currency="RUB",
        vat_rate=20,
        payment_due_date="2026-09-25",
        purpose="консультационные услуги",
        confidence="high",
        missing_fields=[],
        next_action="approve_payment",
        escalate=False,
    )
    base.update(overrides)
    return FinancialExtraction(**base)


def test_full_document_no_escalation():
    r = apply_rules(make())
    assert r.escalate is False
    assert r.missing_fields == []
    assert r.next_action == "approve_payment"


def test_low_confidence_forces_escalation():
    r = apply_rules(make(confidence="low"))
    assert r.escalate is True
    assert r.next_action == "request_clarification"


def test_missing_amount_forces_escalation():
    r = apply_rules(make(amount=None))
    assert r.escalate is True
    assert "amount" in r.missing_fields


def test_missing_counterparty_forces_escalation():
    r = apply_rules(make(counterparty=None))
    assert r.escalate is True
    assert "counterparty" in r.missing_fields


def test_llm_said_escalate_false_but_python_overrides():
    # LLM солгала про escalate — deterministic rules всё равно эскалируют
    r = apply_rules(make(document_number=None, escalate=False))
    assert r.escalate is True
    assert "document_number" in r.missing_fields


def test_zero_amount_escalates():
    r = apply_rules(make(amount=0))
    assert r.escalate is True
    assert "amount" in r.missing_fields


def test_invalid_literal_rejected_by_schema():
    with pytest.raises(ValidationError):
        make(currency="YEN")


def test_negative_amount_rejected_by_schema():
    with pytest.raises(ValidationError):
        make(amount=-5)