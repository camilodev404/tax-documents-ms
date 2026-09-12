from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy.orm import Session

from app.repositories.tax_bracket_repository import IncomeTaxBracketRepository
from app.schemas.tax_bracket import ExtractedIncomeTaxBracket, IncomeTaxBracketCreate
from app.services.tax_document_extractor import PdfDocument, TaxDocumentExtractor

SessionFactory = Callable[[], Session]

TAX_RATE_QUANTIZATION = Decimal("0.0001")


@dataclass(frozen=True)
class DocumentIngestionResult:
    filename: str
    extracted_records: int
    inserted_records: int


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


def normalize_income_max(value: Decimal | str) -> Decimal | None:
    if isinstance(value, str) and value.strip().upper() == "NO_LIMIT":
        return None
    return _to_decimal(value, field_name="income_max")


def normalize_tax_rate(value: Decimal | str) -> Decimal:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.endswith("%"):
            percentage = _to_decimal(stripped[:-1].strip(), field_name="tax_rate")
            return (percentage / Decimal("100")).quantize(TAX_RATE_QUANTIZATION)
        return _to_decimal(stripped, field_name="tax_rate").quantize(TAX_RATE_QUANTIZATION)

    return value.quantize(TAX_RATE_QUANTIZATION)


def normalize_extracted_bracket(
    record: ExtractedIncomeTaxBracket,
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
        extractor: TaxDocumentExtractor,
        repository: IncomeTaxBracketRepository,
    ) -> None:
        self._session_factory = session_factory
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
        document = PdfDocument(filename=path.name, content=path.read_bytes())
        extracted_records = self._extractor.extract(document)
        normalized_records = [
            normalize_extracted_bracket(record, source_document=path.name)
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
            filename=path.name,
            extracted_records=len(extracted_records),
            inserted_records=inserted_records,
        )


def _to_decimal(value: Decimal | str, *, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid decimal value for {field_name}: {value!r}") from exc
