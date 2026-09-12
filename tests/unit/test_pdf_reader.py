from pathlib import Path

import pytest

from app.infrastructure.pdf_reader import PdfReadError, PdfTextReader


def test_pdf_reader_extracts_text_from_2022_fixture() -> None:
    pytest.importorskip("pdfplumber")
    path = Path("data/input/income-tax-brackets-2022.pdf")

    document = PdfTextReader().read(path)

    assert document.filename == "income-tax-brackets-2022.pdf"
    assert "record" in document.text.lower()


def test_pdf_reader_rejects_non_pdf(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("not a pdf")

    with pytest.raises(PdfReadError):
        PdfTextReader().read(path)
