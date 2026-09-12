from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import configure_logging
from app.infrastructure.database import create_session
from app.repositories.tax_bracket_repository import IncomeTaxBracketRepository
from app.schemas.tax_bracket import IncomeTaxBracketCreate
from app.services.tax_bracket_seed import SeedResult, seed_income_tax_brackets

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed income tax bracket records from JSON.")
    parser.add_argument("path", type=Path, help="Path to the income tax bracket seed JSON file.")
    return parser


def main() -> int:
    configure_logging()
    args = build_parser().parse_args()

    try:
        records = _load_seed_records(args.path)
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        logger.error("Seed file is invalid: %s", exc)
        print("received=0 inserted=0 skipped=0 invalid=1")
        return 1

    session = create_session()
    try:
        result = seed_income_tax_brackets(
            session=session,
            records=records,
            repository=IncomeTaxBracketRepository(),
        )
    except SQLAlchemyError as exc:
        logger.error("Seed transaction failed: %s", exc)
        return 1
    finally:
        session.close()

    _print_result(result)
    return 0 if result.invalid_records == 0 else 1


def _load_seed_records(path: Path) -> list[IncomeTaxBracketCreate]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Seed JSON must be a list of records")

    records: list[IncomeTaxBracketCreate] = []
    for item in raw:
        records.append(IncomeTaxBracketCreate.model_validate(_reject_float_values(item)))
    return records


def _reject_float_values(value: Any) -> Any:
    if isinstance(value, float):
        raise ValueError("Seed JSON must encode decimals as strings, not numbers")
    if isinstance(value, dict):
        return {key: _reject_float_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_reject_float_values(item) for item in value]
    return value


def _print_result(result: SeedResult) -> None:
    print(
        f"received={result.received_records} "
        f"inserted={result.inserted_records} "
        f"skipped={result.skipped_records} "
        f"invalid={result.invalid_records}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
