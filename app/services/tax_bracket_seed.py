from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories.tax_bracket_repository import IncomeTaxBracketRepository
from app.schemas.tax_bracket import IncomeTaxBracketCreate


@dataclass(frozen=True)
class SeedResult:
    received_records: int
    inserted_records: int
    skipped_records: int
    invalid_records: int = 0


def seed_income_tax_brackets(
    *,
    session: Session,
    records: list[IncomeTaxBracketCreate],
    repository: IncomeTaxBracketRepository,
) -> SeedResult:
    received = len(records)
    try:
        transaction = nullcontext() if session.in_transaction() else session.begin()
        with transaction:
            inserted = repository.add_many_skip_existing(session, records)
    except Exception:
        session.rollback()
        raise

    return SeedResult(
        received_records=received,
        inserted_records=inserted,
        skipped_records=received - inserted,
        invalid_records=0,
    )
