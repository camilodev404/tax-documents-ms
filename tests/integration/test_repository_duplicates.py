from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models.tax_bracket import IncomeTaxBracket
from app.repositories.tax_bracket_repository import IncomeTaxBracketRepository
from app.schemas.tax_bracket import IncomeTaxBracketCreate


def test_add_many_skip_existing_prevents_duplicates(
    session_factory: sessionmaker[Session],
    cleanup_source_documents: set[str],
) -> None:
    repository = IncomeTaxBracketRepository()
    source_document = f"repository-duplicate-{uuid4()}.pdf"
    cleanup_source_documents.add(source_document)
    record = IncomeTaxBracketCreate(
        source_record_id=1,
        tax_year=2024,
        jurisdiction="US Federal",
        currency="USD",
        income_min=Decimal("0.00"),
        income_max=None,
        tax_rate=Decimal("0.1000"),
        source_document=source_document,
    )

    with session_factory.begin() as session:
        assert repository.add_many_skip_existing(session, [record]) == 1
        assert repository.add_many_skip_existing(session, [record]) == 0
        count = len(
            session.scalars(
                select(IncomeTaxBracket).where(IncomeTaxBracket.source_document == source_document)
            ).all()
        )

    assert count == 1


def test_repository_reads_by_year_and_jurisdiction_and_preserves_decimals(
    session_factory: sessionmaker[Session],
    cleanup_source_documents: set[str],
) -> None:
    repository = IncomeTaxBracketRepository()
    source_document = f"repository-read-{uuid4()}.pdf"
    cleanup_source_documents.add(source_document)
    records = [
        IncomeTaxBracketCreate(
            source_record_id=1,
            tax_year=2026,
            jurisdiction="North Region",
            currency="USD",
            income_min=Decimal("0.00"),
            income_max=Decimal("18000.00"),
            tax_rate=Decimal("0.1000"),
            source_document=source_document,
        ),
        IncomeTaxBracketCreate(
            source_record_id=2,
            tax_year=2026,
            jurisdiction="South Region",
            currency="USD",
            income_min=Decimal("0.00"),
            income_max=None,
            tax_rate=Decimal("0.1000"),
            source_document=source_document,
        ),
    ]

    with session_factory.begin() as session:
        repository.add_many_skip_existing(session, records)
        by_year = repository.list(session, tax_year=2026)
        by_jurisdiction = repository.list(
            session,
            tax_year=2026,
            jurisdiction="South Region",
        )

    scoped_by_year = [record for record in by_year if record.source_document == source_document]

    assert len(scoped_by_year) == 2
    scoped_by_jurisdiction = [
        record for record in by_jurisdiction if record.source_document == source_document
    ]

    assert len(scoped_by_jurisdiction) == 1
    assert scoped_by_jurisdiction[0].income_max is None
    assert scoped_by_jurisdiction[0].tax_rate == Decimal("0.1000")


def test_database_unique_constraint_rejects_duplicate_source_record(
    session_factory: sessionmaker[Session],
    cleanup_source_documents: set[str],
) -> None:
    source_document = f"repository-constraint-{uuid4()}.pdf"
    cleanup_source_documents.add(source_document)
    first = IncomeTaxBracket(
        source_record_id=1,
        tax_year=2027,
        jurisdiction="North Region",
        currency="USD",
        income_min=Decimal("0.00"),
        income_max=None,
        tax_rate=Decimal("0.1000"),
        source_document=source_document,
    )
    duplicate = IncomeTaxBracket(
        source_record_id=1,
        tax_year=2027,
        jurisdiction="North Region",
        currency="USD",
        income_min=Decimal("0.00"),
        income_max=None,
        tax_rate=Decimal("0.1000"),
        source_document=source_document,
    )

    with pytest.raises(IntegrityError):
        with session_factory.begin() as session:
            session.add_all([first, duplicate])


def test_transaction_rolls_back_when_insert_fails(
    session_factory: sessionmaker[Session],
    cleanup_source_documents: set[str],
) -> None:
    source_document = f"repository-rollback-{uuid4()}.pdf"
    cleanup_source_documents.add(source_document)

    with pytest.raises(IntegrityError):
        with session_factory.begin() as session:
            session.add(
                IncomeTaxBracket(
                    source_record_id=1,
                    tax_year=2028,
                    jurisdiction="North Region",
                    currency="USD",
                    income_min=Decimal("0.00"),
                    income_max=None,
                    tax_rate=Decimal("0.1000"),
                    source_document=source_document,
                )
            )
            session.add(
                IncomeTaxBracket(
                    source_record_id=1,
                    tax_year=2028,
                    jurisdiction="North Region",
                    currency="USD",
                    income_min=Decimal("0.00"),
                    income_max=None,
                    tax_rate=Decimal("0.1000"),
                    source_document=source_document,
                )
            )

    with session_factory() as session:
        count = len(
            session.scalars(
                select(IncomeTaxBracket).where(IncomeTaxBracket.source_document == source_document)
            ).all()
        )

    assert count == 0


def test_repository_returns_empty_list_when_no_results(
    session_factory: sessionmaker[Session],
) -> None:
    repository = IncomeTaxBracketRepository()

    with session_factory() as session:
        result = repository.list(session, tax_year=1801)

    assert result == []
