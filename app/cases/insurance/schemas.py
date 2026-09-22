"""Схема извлечения для кейса H — страховой triage."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

ClaimType = Literal[
    "property_damage",
    "transport_damage",
    "theft",
    "accident",
    "unknown",
]
Currency = Literal["RUB", "USD", "EUR", "GBP", "unknown"]
Evidence = Literal[
    "photos",
    "video",
    "contract",
    "acceptance_act",
    "police_report",
    "other",
]
Confidence = Literal["high", "medium", "low"]
NextAction = Literal[
    "register_claim",
    "request_missing_information",
    "manual_review",
]


class InsuranceClaim(BaseModel):
    claim_type: ClaimType
    incident_date: date | None = None
    description: str
    estimated_damage: float | None = Field(default=None, ge=0)
    currency: Currency
    policy_number: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    required_missing: list[str] = Field(default_factory=list)
    confidence: Confidence
    next_action: NextAction
    escalate: bool