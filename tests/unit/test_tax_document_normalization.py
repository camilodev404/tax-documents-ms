from decimal import Decimal

from app.schemas.tax_bracket import ExtractedIncomeTaxBracket
from app.services.tax_document_ingestion import normalize_extracted_bracket


def test_normalizes_no_limit_to_none_and_percentage_to_fraction() -> None:
    extracted = ExtractedIncomeTaxBracket(
        record_id=1,
        tax_year=2024,
        jurisdiction="US Federal",
        currency="USD",
        income_min=Decimal("0.00"),
        income_max="NO_LIMIT",
        tax_rate="10%",
    )

    normalized = normalize_extracted_bracket(extracted, source_document="sample.pdf")

    assert normalized.income_max is None
    assert normalized.tax_rate == Decimal("0.1000")
