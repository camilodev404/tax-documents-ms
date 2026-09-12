from collections.abc import Generator

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.database import get_engine
from app.models.tax_bracket import IncomeTaxBracket


@pytest.fixture(scope="session")
def postgres_session_factory() -> sessionmaker[Session]:
    engine = get_engine()
    if engine.dialect.name != "postgresql":
        pytest.fail("Integration tests require PostgreSQL; SQLite is not allowed here.")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture()
def session_factory(
    postgres_session_factory: sessionmaker[Session],
) -> sessionmaker[Session]:
    return postgres_session_factory


@pytest.fixture()
def cleanup_source_documents(
    postgres_session_factory: sessionmaker[Session],
) -> Generator[set[str], None, None]:
    source_documents: set[str] = set()
    try:
        yield source_documents
    finally:
        if source_documents:
            with postgres_session_factory.begin() as session:
                session.execute(
                    delete(IncomeTaxBracket).where(
                        IncomeTaxBracket.source_document.in_(source_documents)
                    )
                )


@pytest.fixture()
def transactional_session(
    postgres_session_factory: sessionmaker[Session],
) -> Generator[Session, None, None]:
    engine = get_engine()
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
