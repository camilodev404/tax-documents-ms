from __future__ import annotations

from decimal import Decimal

import pytest

from app.infrastructure.ai.extractor import ExtractedTaxBracket
from app.services.tax_bracket_validation import (
    TaxBracketValidationError,
    validate_extracted_tax_brackets,
)


def _record(
    source_record_id: int,
    income_min: str,
    income_max: str | None,
) -> ExtractedTaxBracket:
    return ExtractedTaxBracket(
        source_record_id=source_record_id,
        tax_year=2022,
        jurisdiction="US Federal",
        currency="USD",
        income_min=Decimal(income_min),
        income_max=Decimal(income_max) if income_max is not None else None,
        tax_rate=Decimal("0.10"),
    )


def test_validation_detects_duplicate_rows() -> None:
    with pytest.raises(TaxBracketValidationError):
        validate_extracted_tax_brackets(
            [
                _record(1, "0", "100"),
                _record(1, "100", None),
            ]
        )


def test_validation_detects_non_continuous_ranges() -> None:
    with pytest.raises(TaxBracketValidationError):
        validate_extracted_tax_brackets(
            [
                _record(1, "0", "100"),
                _record(2, "101", None),
            ]
        )


def test_validation_accepts_last_open_ended_bracket() -> None:
    validate_extracted_tax_brackets(
        [
            _record(1, "0", "100"),
            _record(2, "100", None),
        ]
    )
