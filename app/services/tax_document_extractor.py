from dataclasses import dataclass
from typing import Protocol

from app.schemas.tax_bracket import ExtractedIncomeTaxBracket


@dataclass(frozen=True)
class PdfDocument:
    filename: str
    content: bytes


class TaxDocumentExtractor(Protocol):
    def extract(self, document: PdfDocument) -> list[ExtractedIncomeTaxBracket]:
        pass
