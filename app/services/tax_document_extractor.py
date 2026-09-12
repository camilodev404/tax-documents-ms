from typing import Protocol

from app.infrastructure.ai.extractor import ExtractedTaxBrackets


class TaxDocumentExtractor(Protocol):
    def extract(self, *, text: str, source_document: str) -> ExtractedTaxBrackets:
        pass
