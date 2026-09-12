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


def test_health_returns_ok() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_tax_brackets_returns_all_real_seeded_records_in_stable_order() -> None:
    response = TestClient(app).get("/tax-brackets")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 50
    assert payload == sorted(
        payload,
        key=lambda record: (
            record["tax_year"],
            record["jurisdiction"],
            Decimal(record["income_min"]),
            record["source_record_id"],
        ),
    )
    assert payload == TestClient(app).get("/tax-brackets").json()
    assert {
        "source_record_id",
        "tax_year",
        "jurisdiction",
        "currency",
        "income_min",
        "income_max",
        "tax_rate",
        "source_document",
    }.issubset(payload[0])


def test_get_tax_brackets_filters_each_real_year() -> None:
    client = TestClient(app)

    for year in range(2022, 2027):
        response = client.get(f"/tax-brackets?tax_year={year}")
        payload = response.json()

        assert response.status_code == 200
        assert len(payload) == 10
        assert all(record["tax_year"] == year for record in payload)
        assert payload == sorted(
            payload,
            key=lambda record: (
                record["tax_year"],
                record["jurisdiction"],
                Decimal(record["income_min"]),
                record["source_record_id"],
            ),
        )


def test_get_tax_brackets_real_data_serializes_nulls_and_decimals() -> None:
    response = TestClient(app).get("/tax-brackets?tax_year=2022")
    payload = response.json()

    open_ended = [record for record in payload if record["income_max"] is None]

    assert len(open_ended) == 2
    assert {record["source_record_id"] for record in open_ended} == {5, 10}
    assert payload[0]["income_min"] == "0.00"
    assert payload[1]["tax_rate"] == "0.1000"


def test_get_tax_brackets_non_numeric_year_returns_422() -> None:
    response = TestClient(app).get("/tax-brackets?tax_year=not-a-year")

    assert response.status_code == 422
