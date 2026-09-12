from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.infrastructure.ai.extractor import ExtractedTaxBracket
from app.infrastructure.pdf_reader import PdfTextReader
from app.repositories.tax_bracket_repository import IncomeTaxBracketRepository
from app.schemas.tax_bracket import IncomeTaxBracketCreate
from app.services.tax_bracket_validation import validate_extracted_tax_brackets
from app.services.tax_document_extractor import TaxDocumentExtractor

SessionFactory = Callable[[], Session]

TAX_RATE_QUANTIZATION = Decimal("0.0001")


@dataclass(frozen=True)
class DocumentIngestionResult:
    filename: str
    status: str
    extracted_records: int
    valid_records: int
    inserted_records: int
    skipped_records: int
    reason: str | None = None


@dataclass(frozen=True)
class DocumentIngestionFailure:
    filename: str
    error: str


@dataclass(frozen=True)
class IngestionSummary:
    processed: list[DocumentIngestionResult]
    failed: list[DocumentIngestionFailure]


def discover_pdf_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []
    return sorted(
        path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() == ".pdf"
    )


def normalize_income_max(value: Decimal | None) -> Decimal | None:
    return value


def normalize_tax_rate(value: Decimal) -> Decimal:
    return value.quantize(TAX_RATE_QUANTIZATION)


def normalize_extracted_bracket(
    record: ExtractedTaxBracket,
    *,
    source_document: str,
) -> IncomeTaxBracketCreate:
    return IncomeTaxBracketCreate(
        source_record_id=record.source_record_id,
        tax_year=record.tax_year,
        jurisdiction=record.jurisdiction,
        currency=record.currency,
        income_min=record.income_min,
        income_max=normalize_income_max(record.income_max),
        tax_rate=normalize_tax_rate(record.tax_rate),
        source_document=source_document,
    )


class TaxDocumentIngestionService:
    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        pdf_reader: PdfTextReader,
        extractor: TaxDocumentExtractor,
        repository: IncomeTaxBracketRepository,
    ) -> None:
        self._session_factory = session_factory
        self._pdf_reader = pdf_reader
        self._extractor = extractor
        self._repository = repository

    def ingest_all(self, input_dir: Path) -> IngestionSummary:
        return self.ingest_files(discover_pdf_files(input_dir))

    def ingest_files(self, paths: Iterable[Path]) -> IngestionSummary:
        processed: list[DocumentIngestionResult] = []
        failed: list[DocumentIngestionFailure] = []

        for path in paths:
            try:
                processed.append(self.ingest_file(path))
            except Exception as exc:  # noqa: BLE001 - keep batch ingestion moving per document.
                failed.append(DocumentIngestionFailure(filename=path.name, error=str(exc)))

        return IngestionSummary(processed=processed, failed=failed)

    def ingest_file(self, path: Path) -> DocumentIngestionResult:
        existing_records = self._count_existing_records(path.name)
        if existing_records > 0:
            return DocumentIngestionResult(
                filename=path.name,
                status="skipped",
                extracted_records=0,
                valid_records=0,
                inserted_records=0,
                skipped_records=existing_records,
                reason="source_document_already_processed",
            )

        document = self._pdf_reader.read(path)
        extraction = self._extractor.extract(
            text=document.text,
            source_document=document.filename,
        )
        extracted_records = extraction.records
        validate_extracted_tax_brackets(extracted_records)
        normalized_records = [
            normalize_extracted_bracket(record, source_document=document.filename)
            for record in extracted_records
        ]

        session = self._session_factory()
        try:
            with session.begin():
                inserted_records = self._repository.add_many_skip_existing(
                    session, normalized_records
                )
        finally:
            session.close()

        return DocumentIngestionResult(
            filename=document.filename,
            status="processed",
            extracted_records=len(extracted_records),
            valid_records=len(normalized_records),
            inserted_records=inserted_records,
            skipped_records=len(extracted_records) - inserted_records,
        )

    def _count_existing_records(self, source_document: str) -> int:
        session = self._session_factory()
        try:
            return self._repository.count_by_source_document(
                session,
                source_document=source_document,
            )
        finally:
            session.close()
