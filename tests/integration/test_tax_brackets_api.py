from collections.abc import Generator
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_db_session
from app.main import app
from app.models.tax_bracket import IncomeTaxBracket


def test_get_tax_brackets_filters_by_tax_year(session_factory: sessionmaker[Session]) -> None:
    with session_factory.begin() as session:
        session.add_all(
            [
                IncomeTaxBracket(
                    source_record_id=1,
                    tax_year=2024,
                    jurisdiction="US Federal",
                    currency="USD",
                    income_min=Decimal("0.00"),
                    income_max=Decimal("10000.00"),
                    tax_rate=Decimal("0.1000"),
                    source_document="a.pdf",
                ),
                IncomeTaxBracket(
                    source_record_id=2,
                    tax_year=2025,
                    jurisdiction="US Federal",
                    currency="USD",
                    income_min=Decimal("0.00"),
                    income_max=None,
                    tax_rate=Decimal("0.1200"),
                    source_document="b.pdf",
                ),
            ]
        )

    def override_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_session
    try:
        response = TestClient(app).get("/tax-brackets?tax_year=2024")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["tax_year"] == 2024
    assert payload[0]["source_document"] == "a.pdf"


def test_get_tax_brackets_returns_empty_list_when_no_results(
    session_factory: sessionmaker[Session],
) -> None:
    def override_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_session
    try:
        response = TestClient(app).get("/tax-brackets?tax_year=2030")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []


def test_get_tax_brackets_rejects_invalid_filter(session_factory: sessionmaker[Session]) -> None:
    def override_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_session
    try:
        response = TestClient(app).get("/tax-brackets?tax_year=0")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
