from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.infrastructure.ai.extractor import ExtractedTaxBracket, ExtractedTaxBrackets


def test_structured_response_model_accepts_valid_records() -> None:
    extraction = ExtractedTaxBrackets(
        records=[
            {
                "source_record_id": 1,
                "tax_year": 2022,
                "jurisdiction": "US Federal",
                "currency": "usd",
                "income_min": "0",
                "income_max": "10,000",
                "tax_rate": "10%",
            }
        ]
    )

    record = extraction.records[0]

    assert record.currency == "USD"
    assert record.income_max == Decimal("10000")
    assert record.tax_rate == Decimal("0.10")


def test_rejects_invalid_currency() -> None:
    with pytest.raises(ValidationError):
        ExtractedTaxBracket(
            source_record_id=1,
            tax_year=2022,
            jurisdiction="US Federal",
            currency="US",
            income_min=Decimal("0"),
            income_max=None,
            tax_rate=Decimal("0.10"),
        )


def test_validates_income_range() -> None:
    with pytest.raises(ValidationError):
        ExtractedTaxBracket(
            source_record_id=1,
            tax_year=2022,
            jurisdiction="US Federal",
            currency="USD",
            income_min=Decimal("100"),
            income_max=Decimal("100"),
            tax_rate=Decimal("0.10"),
        )


def test_validates_tax_year_range() -> None:
    with pytest.raises(ValidationError):
        ExtractedTaxBracket(
            source_record_id=1,
            tax_year=1700,
            jurisdiction="US Federal",
            currency="USD",
            income_min=Decimal("0"),
            income_max=None,
            tax_rate=Decimal("0.10"),
        )
