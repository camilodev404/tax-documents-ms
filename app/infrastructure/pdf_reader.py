from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class PdfReadError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExtractedPdfText:
    filename: str
    text: str


class PdfTextReader:
    def read(self, path: Path) -> ExtractedPdfText:
        if not path.exists():
            raise PdfReadError(f"PDF file does not exist: {path}")
        if not path.is_file():
            raise PdfReadError(f"PDF path is not a file: {path}")
        if path.suffix.lower() != ".pdf":
            raise PdfReadError(f"Expected a .pdf file, got: {path}")

        try:
            import pdfplumber
        except ImportError as exc:
            raise PdfReadError("pdfplumber is required to read PDF files") from exc

        page_texts: list[str] = []
        try:
            with pdfplumber.open(path) as pdf:
                for index, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text(
                        x_tolerance=1,
                        y_tolerance=3,
                        layout=True,
                    )
                    if text:
                        page_texts.append(f"--- page {index} ---\n{text}")
        except Exception as exc:
            raise PdfReadError(f"Unable to read PDF content from {path.name}") from exc

        text = "\n\n".join(page_texts).strip()
        if not text:
            raise PdfReadError(f"No extractable text found in PDF: {path.name}")

        return ExtractedPdfText(filename=path.name, text=text)
