import argparse
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.infrastructure.ai.langchain_extractor import LangChainTaxDocumentExtractor
from app.infrastructure.database import create_session
from app.infrastructure.pdf_reader import PdfTextReader
from app.repositories.tax_bracket_repository import IncomeTaxBracketRepository
from app.services.tax_document_ingestion import TaxDocumentIngestionService

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest tax bracket PDFs.")
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="PDF file to ingest, for example data/input/income-tax-brackets-2022.pdf.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Directory containing PDF files. Defaults to INPUT_DIR or data/input.",
    )
    return parser


def main() -> int:
    configure_logging()
    settings = get_settings()
    args = build_parser().parse_args()
    input_dir = args.input_dir or settings.input_dir

    service = TaxDocumentIngestionService(
        session_factory=create_session,
        pdf_reader=PdfTextReader(),
        extractor=LangChainTaxDocumentExtractor(
            api_key=settings.openai_api_key,
            model_name=settings.openai_model,
            temperature=settings.openai_temperature,
        ),
        repository=IncomeTaxBracketRepository(),
    )

    summary = service.ingest_files([args.file]) if args.file else service.ingest_all(input_dir)
    for result in summary.processed:
        logger.info(
            "Processed %s: status=%s extracted=%s valid=%s inserted=%s skipped=%s reason=%s",
            result.filename,
            result.status,
            result.extracted_records,
            result.valid_records,
            result.inserted_records,
            result.skipped_records,
            result.reason,
        )

    for failure in summary.failed:
        logger.error("Failed %s: %s", failure.filename, failure.error)

    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
