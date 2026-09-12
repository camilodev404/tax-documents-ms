from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.ai.extractor import ExtractedTaxBracket, ExtractedTaxBrackets
from app.infrastructure.pdf_reader import ExtractedPdfText
from app.models.tax_bracket import IncomeTaxBracket
from app.repositories.tax_bracket_repository import IncomeTaxBracketRepository
from app.services.tax_bracket_validation import TaxBracketValidationError
from app.services.tax_document_ingestion import TaxDocumentIngestionService


@dataclass
class FakePdfReader:
    text: str = "table text"
    filename: str = "sample.pdf"

    def read(self, path: Path) -> ExtractedPdfText:
        return ExtractedPdfText(filename=self.filename, text=self.text)


class FakeExtractor:
    def __init__(self, records: list[ExtractedTaxBracket]) -> None:
        self._records = records

    def extract(self, *, text: str, source_document: str) -> ExtractedTaxBrackets:
        return ExtractedTaxBrackets(records=self._records)


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


def _service(
    session_factory: sessionmaker[Session],
    records: list[ExtractedTaxBracket],
) -> TaxDocumentIngestionService:
    return TaxDocumentIngestionService(
        session_factory=session_factory,
        pdf_reader=FakePdfReader(),
        extractor=FakeExtractor(records),
        repository=IncomeTaxBracketRepository(),
    )


def test_ingestion_is_idempotent_for_same_document(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    path = tmp_path / "sample.pdf"
    path.write_bytes(b"%PDF")
    service = _service(
        session_factory,
        [
            _record(1, "0", "100"),
            _record(2, "100", None),
        ],
    )

    first = service.ingest_file(path)
    second = service.ingest_file(path)

    with session_factory() as session:
        count = len(session.scalars(select(IncomeTaxBracket)).all())

    assert first.inserted_records == 2
    assert first.skipped_records == 0
    assert second.inserted_records == 0
    assert second.skipped_records == 2
    assert count == 2


def test_ingestion_does_not_persist_partial_document_when_validation_fails(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    path = tmp_path / "sample.pdf"
    path.write_bytes(b"%PDF")
    service = _service(
        session_factory,
        [
            _record(1, "0", "100"),
            _record(1, "100", None),
        ],
    )

    with pytest.raises(TaxBracketValidationError):
        service.ingest_file(path)

    with session_factory() as session:
        count = len(session.scalars(select(IncomeTaxBracket)).all())

    assert count == 0
