from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

REASONABLE_MIN_TAX_YEAR = 1900
REASONABLE_MAX_TAX_YEAR = 2200


class AIExtractorNotConfiguredError(RuntimeError):
    pass


class TaxDocumentExtractionError(RuntimeError):
    pass


class ExtractedTaxBracket(BaseModel):
    source_record_id: int = Field(gt=0)
    tax_year: int = Field(ge=REASONABLE_MIN_TAX_YEAR, le=REASONABLE_MAX_TAX_YEAR)
    jurisdiction: str = Field(min_length=1, max_length=120)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    income_min: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    income_max: Optional[Decimal] = Field(default=None, max_digits=18, decimal_places=2)
    tax_rate: Decimal = Field(ge=0, le=1, max_digits=7, decimal_places=4)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("income_min", "income_max", "tax_rate", mode="before")
    @classmethod
    def normalize_decimal_values(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, float):
            raise TypeError("Use Decimal or string input, never float")
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.upper() == "NO_LIMIT":
                return None
            normalized = stripped.replace(",", "")
            if normalized.endswith("%"):
                return _decimal(normalized[:-1].strip()) / Decimal("100")
            return _decimal(normalized)
        return value

    @model_validator(mode="after")
    def validate_income_range(self) -> ExtractedTaxBracket:
        if self.income_max is not None and self.income_max <= self.income_min:
            raise ValueError("income_max must be greater than income_min when present")
        return self


class ExtractedTaxBrackets(BaseModel):
    records: list[ExtractedTaxBracket] = Field(default_factory=list)


def _decimal(value: str) -> Decimal:
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid decimal value: {value!r}") from exc
