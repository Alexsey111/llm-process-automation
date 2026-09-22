"""Схема извлечения для кейса F — финансовые документы."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

DocumentType = Literal["invoice", "expense_request", "payment_order", "unknown"]
Currency = Literal["RUB", "USD", "EUR", "GBP", "unknown"]
Confidence = Literal["high", "medium", "low"]
NextAction = Literal["approve_payment", "request_clarification", "manual_review"]


class FinancialExtraction(BaseModel):
    document_type: DocumentType
    document_number: str | None = None
    document_date: date | None = None
    counterparty: str | None = None
    amount: float | None = Field(default=None, ge=0)
    currency: Currency
    vat_rate: float | None = Field(default=None, ge=0, le=100)
    payment_due_date: date | None = None
    purpose: str | None = None
    confidence: Confidence
    missing_fields: list[str] = Field(default_factory=list)
    next_action: NextAction
    escalate: bool