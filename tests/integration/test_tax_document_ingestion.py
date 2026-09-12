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
    filename: str = "fake-income-tax-brackets-2022.pdf"
    read_count: int = 0

    def read(self, path: Path) -> ExtractedPdfText:
        self.read_count += 1
        return ExtractedPdfText(filename=self.filename, text=self.text)


class FakeExtractor:
    def __init__(self, records: list[ExtractedTaxBracket]) -> None:
        self._records = records
        self.calls = 0

    def extract(self, *, text: str, source_document: str) -> ExtractedTaxBrackets:
        self.calls += 1
        return ExtractedTaxBrackets(records=self._records)


class FailingExtractor:
    calls = 0

    def extract(self, *, text: str, source_document: str) -> ExtractedTaxBrackets:
        self.calls += 1
        raise AssertionError("Extractor must not be called for existing documents")


class FailingRepository(IncomeTaxBracketRepository):
    def add_many_skip_existing(self, session: Session, records: list) -> int:
        session.add(IncomeTaxBracket(**records[0].model_dump()))
        session.flush()
        raise RuntimeError("Simulated persistence failure")


def _record(
    source_record_id: int,
    income_min: str,
    income_max: str | None,
    *,
    jurisdiction: str = "US Federal",
    tax_rate: str = "0.10",
) -> ExtractedTaxBracket:
    return ExtractedTaxBracket(
        source_record_id=source_record_id,
        tax_year=2022,
        jurisdiction=jurisdiction,
        currency="USD",
        income_min=Decimal(income_min),
        income_max=Decimal(income_max) if income_max is not None else None,
        tax_rate=Decimal(tax_rate),
    )


def _service(
    session_factory: sessionmaker[Session],
    records: list[ExtractedTaxBracket],
    *,
    source_document: str = "fake-income-tax-brackets-2022.pdf",
) -> TaxDocumentIngestionService:
    extractor = FakeExtractor(records)
    return _service_with_dependencies(
        session_factory,
        pdf_reader=FakePdfReader(filename=source_document),
        extractor=extractor,
    )


def _service_with_dependencies(
    session_factory: sessionmaker[Session],
    *,
    pdf_reader: FakePdfReader,
    extractor: FakeExtractor | FailingExtractor,
) -> TaxDocumentIngestionService:
    return TaxDocumentIngestionService(
        session_factory=session_factory,
        pdf_reader=pdf_reader,
        extractor=extractor,
        repository=IncomeTaxBracketRepository(),
    )


def test_ingestion_is_idempotent_for_same_document(
    session_factory: sessionmaker[Session],
    cleanup_source_documents: set[str],
    tmp_path: Path,
) -> None:
    source_document = "fake-income-tax-brackets-2022.pdf"
    cleanup_source_documents.add(source_document)
    with session_factory.begin() as session:
        session.query(IncomeTaxBracket).filter(
            IncomeTaxBracket.source_document == source_document
        ).delete(synchronize_session=False)

    path = tmp_path / source_document
    path.write_bytes(b"%PDF")
    service = _service(
        session_factory,
        [
            _record(1, "0", "18000", jurisdiction="North Region", tax_rate="0"),
            _record(2, "18000", "36000", jurisdiction="North Region", tax_rate="0.10"),
            _record(3, "36000", "65000", jurisdiction="North Region", tax_rate="0.18"),
            _record(4, "65000", "110000", jurisdiction="North Region", tax_rate="0.25"),
            _record(5, "110000", None, jurisdiction="North Region", tax_rate="0.35"),
            _record(6, "0", "16000", jurisdiction="South Region", tax_rate="0"),
            _record(7, "16000", "34000", jurisdiction="South Region", tax_rate="0.09"),
            _record(8, "34000", "68000", jurisdiction="South Region", tax_rate="0.17"),
            _record(9, "68000", "115000", jurisdiction="South Region", tax_rate="0.26"),
            _record(10, "115000", None, jurisdiction="South Region", tax_rate="0.34"),
        ],
        source_document=source_document,
    )

    first = service.ingest_file(path)
    second = service.ingest_file(path)

    with session_factory() as session:
        count = len(
            session.scalars(
                select(IncomeTaxBracket).where(IncomeTaxBracket.source_document == source_document)
            ).all()
        )

    assert first.inserted_records == 10
    assert first.valid_records == 10
    assert first.skipped_records == 0
    assert first.status == "processed"
    assert second.inserted_records == 0
    assert second.valid_records == 0
    assert second.skipped_records == 10
    assert second.status == "skipped"
    assert second.reason == "source_document_already_processed"
    assert count == 10


def test_new_document_invokes_extractor_once(
    session_factory: sessionmaker[Session],
    cleanup_source_documents: set[str],
    tmp_path: Path,
) -> None:
    source_document = "new-document-invokes-extractor.pdf"
    cleanup_source_documents.add(source_document)
    path = tmp_path / source_document
    path.write_bytes(b"%PDF")
    pdf_reader = FakePdfReader(filename=source_document)
    extractor = FakeExtractor(
        [
            _record(1, "0", "100"),
            _record(2, "100", None),
        ]
    )
    service = _service_with_dependencies(
        session_factory,
        pdf_reader=pdf_reader,
        extractor=extractor,
    )

    result = service.ingest_file(path)

    assert result.status == "processed"
    assert result.inserted_records == 2
    assert extractor.calls == 1
    assert pdf_reader.read_count == 1


def test_existing_document_skips_before_reading_or_extracting(
    session_factory: sessionmaker[Session],
    cleanup_source_documents: set[str],
    tmp_path: Path,
) -> None:
    source_document = "existing-document-skips.pdf"
    cleanup_source_documents.add(source_document)
    path = tmp_path / source_document
    path.write_bytes(b"%PDF")
    with session_factory.begin() as session:
        session.add(
            IncomeTaxBracket(
                source_record_id=1,
                tax_year=2022,
                jurisdiction="US Federal",
                currency="USD",
                income_min=Decimal("0.00"),
                income_max=None,
                tax_rate=Decimal("0.1000"),
                source_document=source_document,
            )
        )
    pdf_reader = FakePdfReader(filename=source_document)
    service = _service_with_dependencies(
        session_factory,
        pdf_reader=pdf_reader,
        extractor=FailingExtractor(),
    )

    result = service.ingest_file(path)

    assert result.status == "skipped"
    assert result.inserted_records == 0
    assert result.skipped_records == 1
    assert result.reason == "source_document_already_processed"
    assert pdf_reader.read_count == 0


def test_ingestion_does_not_persist_partial_document_when_validation_fails(
    session_factory: sessionmaker[Session],
    cleanup_source_documents: set[str],
    tmp_path: Path,
) -> None:
    source_document = "invalid-ingestion.pdf"
    cleanup_source_documents.add(source_document)
    path = tmp_path / source_document
    path.write_bytes(b"%PDF")
    service = _service(
        session_factory,
        [
            _record(1, "0", "100"),
            _record(1, "100", None),
        ],
        source_document=source_document,
    )

    with pytest.raises(TaxBracketValidationError):
        service.ingest_file(path)

    with session_factory() as session:
        count = len(
            session.scalars(
                select(IncomeTaxBracket).where(IncomeTaxBracket.source_document == source_document)
            ).all()
        )

    assert count == 0


def test_ingestion_rolls_back_when_persistence_fails(
    session_factory: sessionmaker[Session],
    cleanup_source_documents: set[str],
    tmp_path: Path,
) -> None:
    source_document = "persistence-failure-rolls-back.pdf"
    cleanup_source_documents.add(source_document)
    path = tmp_path / source_document
    path.write_bytes(b"%PDF")
    service = TaxDocumentIngestionService(
        session_factory=session_factory,
        pdf_reader=FakePdfReader(filename=source_document),
        extractor=FakeExtractor(
            [
                _record(1, "0", "100"),
                _record(2, "100", None),
            ]
        ),
        repository=FailingRepository(),
    )

    with pytest.raises(RuntimeError, match="Simulated persistence failure"):
        service.ingest_file(path)

    with session_factory() as session:
        count = len(
            session.scalars(
                select(IncomeTaxBracket).where(IncomeTaxBracket.source_document == source_document)
            ).all()
        )

    assert count == 0
