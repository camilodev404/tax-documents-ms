from __future__ import annotations

from sqlalchemy import Select, func, select, tuple_
from sqlalchemy.orm import Session

from app.models.tax_bracket import IncomeTaxBracket
from app.schemas.tax_bracket import IncomeTaxBracketCreate


class IncomeTaxBracketRepository:
    def count_by_source_document(
        self,
        session: Session,
        *,
        source_document: str,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(IncomeTaxBracket)
            .where(IncomeTaxBracket.source_document == source_document)
        )
        return int(session.scalar(statement) or 0)

    def list(
        self,
        session: Session,
        *,
        tax_year: int | None = None,
        jurisdiction: str | None = None,
    ) -> list[IncomeTaxBracket]:
        statement: Select[tuple[IncomeTaxBracket]] = select(IncomeTaxBracket).order_by(
            IncomeTaxBracket.tax_year,
            IncomeTaxBracket.jurisdiction,
            IncomeTaxBracket.income_min,
            IncomeTaxBracket.source_record_id,
        )
        if tax_year is not None:
            statement = statement.where(IncomeTaxBracket.tax_year == tax_year)
        if jurisdiction is not None:
            statement = statement.where(IncomeTaxBracket.jurisdiction == jurisdiction)

        return list(session.scalars(statement).all())

    def add_many_skip_existing(
        self,
        session: Session,
        records: list[IncomeTaxBracketCreate],
    ) -> int:
        if not records:
            return 0

        keys = [(record.source_document, record.source_record_id) for record in records]
        existing_statement = select(
            IncomeTaxBracket.source_document,
            IncomeTaxBracket.source_record_id,
        ).where(
            tuple_(IncomeTaxBracket.source_document, IncomeTaxBracket.source_record_id).in_(keys)
        )
        existing_keys = set(session.execute(existing_statement).all())

        created = 0
        for record in records:
            key = (record.source_document, record.source_record_id)
            if key in existing_keys:
                continue
            session.add(IncomeTaxBracket(**record.model_dump()))
            existing_keys.add(key)
            created += 1

        session.flush()
        return created
