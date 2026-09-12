from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.tax_bracket import IncomeTaxBracketCreate


def test_persistence_schema_rejects_float_values() -> None:
    with pytest.raises((TypeError, ValidationError)):
        IncomeTaxBracketCreate(
            source_record_id=1,
            tax_year=2024,
            jurisdiction="US Federal",
            currency="USD",
            income_min=0.0,
            income_max=None,
            tax_rate=Decimal("0.10"),
            source_document="sample.pdf",
        )


def test_persistence_schema_normalizes_currency() -> None:
    record = IncomeTaxBracketCreate(
        source_record_id=1,
        tax_year=2024,
        jurisdiction="US Federal",
        currency="usd",
        income_min=Decimal("0.00"),
        income_max=None,
        tax_rate=Decimal("0.1000"),
        source_document="sample.pdf",
    )

    assert record.currency == "USD"
