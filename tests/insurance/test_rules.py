"""Unit-тесты deterministic business-rules кейса H (без LLM)."""
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.cases.insurance.rules import apply_rules
from app.cases.insurance.schemas import InsuranceClaim


def make(**overrides):
    base = dict(
        claim_type="transport_damage",
        incident_date="2026-09-18",
        description="Повреждение корпуса оборудования при перевозке",
        estimated_damage=180000.0,
        currency="RUB",
        policy_number="ПОЛИС-2024-778899",
        evidence=["photos", "acceptance_act"],
        required_missing=[],
        confidence="high",
        next_action="register_claim",
        escalate=False,
    )
    base.update(overrides)
    return InsuranceClaim(**base)


def test_full_claim_no_escalation():
    r = apply_rules(make())
    assert r.escalate is False
    assert r.required_missing == []
    assert r.next_action == "register_claim"


def test_missing_policy_number_escalates():
    r = apply_rules(make(policy_number=None))
    assert r.escalate is True
    assert "policy_number" in r.required_missing
    assert r.next_action == "request_missing_information"


def test_missing_date_escalates():
    r = apply_rules(make(incident_date=None))
    assert r.escalate is True
    assert "incident_date" in r.required_missing


def test_no_evidence_escalates():
    r = apply_rules(make(evidence=[]))
    assert r.escalate is True
    assert "evidence" in r.required_missing


def test_llm_overrides_are_corrected_by_python():
    # LLM утверждает, что всё хорошо — Python исправляет состояние
    r = apply_rules(make(policy_number=None, escalate=False))
    assert r.escalate is True


def test_unknown_claim_type_rejected_by_schema():
    with pytest.raises(ValidationError):
        make(claim_type="lottery_win")


def test_negative_damage_rejected_by_schema():
    with pytest.raises(ValidationError):
        make(estimated_damage=-100)