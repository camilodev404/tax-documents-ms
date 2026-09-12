from collections.abc import Generator

from sqlalchemy.orm import Session

from app.infrastructure.database import get_session
from app.repositories.tax_bracket_repository import IncomeTaxBracketRepository
from app.services.tax_bracket_service import IncomeTaxBracketService


def get_db_session() -> Generator[Session, None, None]:
    yield from get_session()


def get_tax_bracket_service() -> IncomeTaxBracketService:
    return IncomeTaxBracketService(repository=IncomeTaxBracketRepository())
