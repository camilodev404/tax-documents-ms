import os
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.infrastructure.ai.langchain_extractor import LangChainTaxDocumentExtractor
from app.infrastructure.pdf_reader import PdfTextReader


@pytest.mark.openai_integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY is not configured")
def test_openai_extracts_2022_pdf_records() -> None:
    settings = get_settings()
    document = PdfTextReader().read(Path("data/input/income-tax-brackets-2022.pdf"))
    extractor = LangChainTaxDocumentExtractor(
        api_key=settings.openai_api_key,
        model_name=settings.openai_model,
        temperature=settings.openai_temperature,
    )

    extraction = extractor.extract(text=document.text, source_document=document.filename)

    assert len(extraction.records) == 10
