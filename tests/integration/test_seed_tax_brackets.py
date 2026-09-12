from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.cli.seed_tax_brackets import _load_seed_records
from app.models.tax_bracket import IncomeTaxBracket
from app.repositories.tax_bracket_repository import IncomeTaxBracketRepository
from app.services.tax_bracket_seed import seed_income_tax_brackets

SEED_PATH = Path("data/seed/income_tax_brackets.json")


def test_seed_skips_existing_real_records(transactional_session: Session) -> None:
    records = _load_seed_records(SEED_PATH)

    result = seed_income_tax_brackets(
        session=transactional_session,
        records=records,
        repository=IncomeTaxBracketRepository(),
    )

    assert result.received_records == 50
    assert result.inserted_records == 0
    assert result.skipped_records == 50
    assert result.invalid_records == 0


def test_seed_inserts_50_into_empty_database_and_second_run_skips(
    transactional_session: Session,
) -> None:
    records = _load_seed_records(SEED_PATH)
    transactional_session.execute(delete(IncomeTaxBracket))

    first = seed_income_tax_brackets(
        session=transactional_session,
        records=records,
        repository=IncomeTaxBracketRepository(),
    )
    second = seed_income_tax_brackets(
        session=transactional_session,
        records=records,
        repository=IncomeTaxBracketRepository(),
    )
    count = transactional_session.scalar(select(func.count()).select_from(IncomeTaxBracket))

    assert first.received_records == 50
    assert first.inserted_records == 50
    assert first.skipped_records == 0
    assert second.received_records == 50
    assert second.inserted_records == 0
    assert second.skipped_records == 50
    assert count == 50
