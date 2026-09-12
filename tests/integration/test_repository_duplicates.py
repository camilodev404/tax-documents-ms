from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.tax_bracket import IncomeTaxBracket
from app.repositories.tax_bracket_repository import IncomeTaxBracketRepository
from app.schemas.tax_bracket import IncomeTaxBracketCreate


def test_add_many_skip_existing_prevents_duplicates(
    session_factory: sessionmaker[Session],
) -> None:
    repository = IncomeTaxBracketRepository()
    record = IncomeTaxBracketCreate(
        source_record_id=1,
        tax_year=2024,
        jurisdiction="US Federal",
        currency="USD",
        income_min=Decimal("0.00"),
        income_max=None,
        tax_rate=Decimal("0.1000"),
        source_document="sample.pdf",
    )

    with session_factory.begin() as session:
        assert repository.add_many_skip_existing(session, [record]) == 1
        assert repository.add_many_skip_existing(session, [record]) == 0
        count = len(session.scalars(select(IncomeTaxBracket)).all())

    assert count == 1
