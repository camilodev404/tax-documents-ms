from pathlib import Path

import pytest

from app.cli.seed_tax_brackets import _load_seed_records


def test_seed_loader_rejects_float_decimals(tmp_path: Path) -> None:
    path = tmp_path / "seed.json"
    path.write_text(
        """
        [
          {
            "source_record_id": 1,
            "tax_year": 2022,
            "jurisdiction": "North Region",
            "currency": "USD",
            "income_min": 0.0,
            "income_max": null,
            "tax_rate": "0.1000",
            "source_document": "sample.pdf"
          }
        ]
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="decimals as strings"):
        _load_seed_records(path)
