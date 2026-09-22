"""Детерминированные business-правила кейса H (уровень 2 контроля качества).

LLM структурирует заявление, но решение об эскалации принимает Python.
"""
from typing import Any

from .schemas import InsuranceClaim

# Без этих полей заявление нельзя зарегистрировать автоматически.
REQUIRED_FIELDS = ("incident_date", "description", "policy_number")


def apply_rules(result: InsuranceClaim) -> InsuranceClaim:
    escalate = bool(result.escalate)

    if result.confidence == "low":
        escalate = True

    missing = {name for name in result.required_missing if name}
    for field in REQUIRED_FIELDS:
        value = getattr(result, field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.add(field)
    if not result.description.strip():
        missing.add("description")
    if missing:
        escalate = True

    if result.estimated_damage is not None and result.estimated_damage <= 0:
        missing.add("estimated_damage")
        escalate = True

    # Отсутствие любых доказательств — повышенный риск, эскалируем.
    if not result.evidence:
        missing.add("evidence")
        escalate = True

    result.required_missing = sorted(missing)
    result.escalate = escalate

    if escalate and result.next_action == "register_claim":
        result.next_action = (
            "request_missing_information"
            if missing
            else "manual_review"
        )

    return result


def to_dict(result: InsuranceClaim) -> dict[str, Any]:
    return result.model_dump(mode="json")