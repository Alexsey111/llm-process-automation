"""Детерминированные business-правила кейса F (уровень 2 контроля качества).

LLM даёт рекомендацию, Python-правила выносят окончательное решение по escalate.
"""
from typing import Any

from .schemas import FinancialExtraction

# Поля, без которых финансовый документ нельзя провести автоматически.
REQUIRED_FIELDS = ("document_number", "counterparty", "amount")


def apply_rules(result: FinancialExtraction) -> FinancialExtraction:
    escalate = bool(result.escalate)

    if result.confidence == "low":
        escalate = True

    missing = {name for name in result.missing_fields if name}
    for field in REQUIRED_FIELDS:
        value = getattr(result, field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.add(field)
    if missing:
        escalate = True

    if not missing and result.amount is not None and result.amount <= 0:
        missing.add("amount")
        escalate = True

    result.missing_fields = sorted(missing)
    result.escalate = escalate

    # next_action согласуем с финальным решением deterministic rules
    if escalate:
        if result.next_action == "approve_payment":
            result.next_action = "request_clarification"
    elif result.next_action == "manual_review":
        result.next_action = "approve_payment"

    return result


def to_dict(result: FinancialExtraction) -> dict[str, Any]:
    return result.model_dump(mode="json")