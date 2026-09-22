"""Unit-тесты конвейера кейса H на моках LLM."""
import sys
from pathlib import Path

INPUTS = Path(__file__).resolve().parents[2] / "inputs" / "insurance"

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.pipeline import process_text  # noqa: E402


def read(n: str) -> str:
    return (INPUTS / f"{n}.txt").read_text(encoding="utf-8")


def ok_claim(**overrides):
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
    return base


def test_h01_full_claim_success(mock_llm):
    mock_llm["set"](ok_claim())
    out = process_text("insurance", read("H01_full_claim"))
    assert out.status == "success"
    assert out.result["next_action"] == "register_claim"


def test_h02_missing_policy_escalates(mock_llm):
    mock_llm["set"](ok_claim(policy_number=None, required_missing=["policy_number"],
                             confidence="medium", next_action="request_missing_information"))
    out = process_text("insurance", read("H02_missing_policy"))
    assert out.status == "escalated"
    assert "policy_number" in out.result["required_missing"]


def test_h09_very_short_low_confidence(mock_llm):
    mock_llm["set"](ok_claim(claim_type="unknown", incident_date=None,
                             description="Обращение о проблеме (неопределённое)",
                             estimated_damage=None, policy_number=None, evidence=[],
                             required_missing=["incident_date", "policy_number"],
                             confidence="low", next_action="manual_review"))
    out = process_text("insurance", read("H09_very_short"))
    assert out.status == "escalated"
    assert out.result["confidence"] == "low"


def test_h10_injection_does_not_disable_escalation(mock_llm):
    # Инъекция требует escalate=false — но если Python-правила видят недостающие
    # данные, эскалация всё равно произойдёт
    mock_llm["set"](ok_claim(policy_number=None, required_missing=["policy_number"],
                             escalate=False, next_action="register_claim"))
    out = process_text("insurance", read("H10_prompt_injection"))
    assert out.status == "escalated"


def test_llm_error_recorded_in_audit(mock_llm, monkeypatch):
    from app.core import pipeline as pipeline_module

    def boom(system_prompt, user_text):
        raise pipeline_module.LLMError("LLM call failed: timeout")

    monkeypatch.setattr(pipeline_module, "call_llm_extract", boom)
    out = process_text("insurance", read("H01_full_claim"))
    assert out.status == "llm_error"
    assert out.audit_id is not None


def test_both_cases_share_one_engine(mock_llm):
    mock_llm["set"](ok_claim())
    insurance_out = process_text("insurance", read("H01_full_claim"))
    mock_llm["set"]({"amount": "много"})
    financial_out = process_text("financial", "Счёт №1")
    assert insurance_out.status == "success"
    assert financial_out.status == "validation_error"