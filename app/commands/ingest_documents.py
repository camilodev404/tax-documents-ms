import argparse
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.infrastructure.ai.langchain_extractor import LangChainTaxDocumentExtractor
from app.infrastructure.database import create_session
from app.repositories.tax_bracket_repository import IncomeTaxBracketRepository
from app.services.tax_document_ingestion import TaxDocumentIngestionService

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest tax bracket PDFs from a directory.")
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
        extractor=LangChainTaxDocumentExtractor(
            api_key=settings.ai_api_key,
            model_name=settings.ai_model_name,
        ),
        repository=IncomeTaxBracketRepository(),
    )

    summary = service.ingest_all(input_dir)
    for result in summary.processed:
        logger.info(
            "Processed %s: extracted=%s inserted=%s",
            result.filename,
            result.extracted_records,
            result.inserted_records,
        )

    for failure in summary.failed:
        logger.error("Failed %s: %s", failure.filename, failure.error)

    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
