"""Реестр кейсов: предметная логика подключается к общему engine через эту таблицу."""
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel

from .financial import prompt as financial_prompt
from .financial import rules as financial_rules
from .financial.schemas import FinancialExtraction
from .insurance import prompt as insurance_prompt
from .insurance import rules as insurance_rules
from .insurance.schemas import InsuranceClaim


@dataclass(frozen=True)
class CaseConfig:
    case_type: str
    schema: type[BaseModel]
    system_prompt: str
    apply_rules: Callable[[BaseModel], BaseModel]
    to_dict: Callable[[BaseModel], dict[str, Any]]


CASES: dict[str, CaseConfig] = {
    "financial": CaseConfig(
        case_type="financial",
        schema=FinancialExtraction,
        system_prompt=financial_prompt.SYSTEM_PROMPT,
        apply_rules=financial_rules.apply_rules,  # type: ignore[arg-type]
        to_dict=financial_rules.to_dict,  # type: ignore[arg-type]
    ),
    "insurance": CaseConfig(
        case_type="insurance",
        schema=InsuranceClaim,
        system_prompt=insurance_prompt.SYSTEM_PROMPT,
        apply_rules=insurance_rules.apply_rules,  # type: ignore[arg-type]
        to_dict=insurance_rules.to_dict,  # type: ignore[arg-type]
    ),
}

DEFAULT_CASE = "financial"


def get_case(case_type: str) -> CaseConfig:
    if case_type not in CASES:
        raise KeyError(
            f"Unknown case_type={case_type!r}; available: {', '.join(CASES)}"
        )
    return CASES[case_type]