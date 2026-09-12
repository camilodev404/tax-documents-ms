from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.tax_bracket import IncomeTaxBracket
from app.repositories.tax_bracket_repository import IncomeTaxBracketRepository


class IncomeTaxBracketService:
    def __init__(self, *, repository: IncomeTaxBracketRepository) -> None:
        self._repository = repository

    def list_brackets(
        self,
        *,
        session: Session,
        tax_year: int | None = None,
    ) -> list[IncomeTaxBracket]:
        return self._repository.list(session=session, tax_year=tax_year)
