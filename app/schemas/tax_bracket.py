from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

MoneyDecimal = Annotated[Decimal, Field(max_digits=18, decimal_places=2, ge=0)]
RateDecimal = Annotated[Decimal, Field(max_digits=7, decimal_places=4, ge=0, le=1)]


def _reject_float(value: object) -> object:
    if isinstance(value, float):
        raise TypeError("Use Decimal or string input, never float")
    return value


class IncomeTaxBracketCreate(BaseModel):
    source_record_id: Annotated[int, Field(gt=0)]
    tax_year: Annotated[int, Field(gt=0)]
    jurisdiction: Annotated[str, Field(min_length=1, max_length=120)]
    currency: Annotated[str, Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")]
    income_min: MoneyDecimal
    income_max: Optional[MoneyDecimal]
    tax_rate: RateDecimal
    source_document: Annotated[str, Field(min_length=1, max_length=255)]

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("income_min", "income_max", "tax_rate", mode="before")
    @classmethod
    def reject_float_values(cls, value: object) -> object:
        return _reject_float(value)


class IncomeTaxBracketResponse(BaseModel):
    id: UUID
    source_record_id: int
    tax_year: int
    jurisdiction: str
    currency: str
    income_min: Decimal
    income_max: Optional[Decimal]
    tax_rate: Decimal
    source_document: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
