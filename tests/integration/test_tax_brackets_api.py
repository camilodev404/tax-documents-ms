from collections.abc import Generator
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_db_session
from app.main import app
from app.models.tax_bracket import IncomeTaxBracket


def test_get_tax_brackets_filters_by_tax_year(
    session_factory: sessionmaker[Session],
    cleanup_source_documents: set[str],
) -> None:
    source_a = f"api-a-{uuid4()}.pdf"
    source_b = f"api-b-{uuid4()}.pdf"
    cleanup_source_documents.update({source_a, source_b})
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
                    source_document=source_a,
                ),
                IncomeTaxBracket(
                    source_record_id=2,
                    tax_year=2025,
                    jurisdiction="US Federal",
                    currency="USD",
                    income_min=Decimal("0.00"),
                    income_max=None,
                    tax_rate=Decimal("0.1200"),
                    source_document=source_b,
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
    scoped_payload = [record for record in payload if record["source_document"] == source_a]
    assert len(scoped_payload) == 1
    assert scoped_payload[0]["tax_year"] == 2024
    assert scoped_payload[0]["source_document"] == source_a


def test_get_tax_brackets_filters_by_jurisdiction(
    session_factory: sessionmaker[Session],
    cleanup_source_documents: set[str],
) -> None:
    source_document = f"api-jurisdiction-{uuid4()}.pdf"
    cleanup_source_documents.add(source_document)
    with session_factory.begin() as session:
        session.add_all(
            [
                IncomeTaxBracket(
                    source_record_id=1,
                    tax_year=2022,
                    jurisdiction="North Region",
                    currency="USD",
                    income_min=Decimal("0.00"),
                    income_max=None,
                    tax_rate=Decimal("0.1000"),
                    source_document=source_document,
                ),
                IncomeTaxBracket(
                    source_record_id=2,
                    tax_year=2022,
                    jurisdiction="South Region",
                    currency="USD",
                    income_min=Decimal("0.00"),
                    income_max=None,
                    tax_rate=Decimal("0.1000"),
                    source_document=source_document,
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
        response = TestClient(app).get("/tax-brackets?tax_year=2022&jurisdiction=North%20Region")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = [record for record in response.json() if record["source_document"] == source_document]
    assert len(payload) == 1
    assert payload[0]["jurisdiction"] == "North Region"


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
        response = TestClient(app).get(
            "/tax-brackets?tax_year=2030&jurisdiction=NoSuchJurisdiction"
        )
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
