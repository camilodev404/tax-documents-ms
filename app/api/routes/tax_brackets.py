from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_tax_bracket_service
from app.schemas.tax_bracket import IncomeTaxBracketResponse
from app.services.tax_bracket_service import IncomeTaxBracketService

router = APIRouter(tags=["tax-brackets"])


@router.get("/tax-brackets", response_model=list[IncomeTaxBracketResponse])
def list_tax_brackets(
    tax_year: Annotated[Optional[int], Query(gt=0)] = None,
    jurisdiction: Annotated[Optional[str], Query(min_length=1, max_length=120)] = None,
    session: Session = Depends(get_db_session),
    service: IncomeTaxBracketService = Depends(get_tax_bracket_service),
) -> list[IncomeTaxBracketResponse]:
    brackets = service.list_brackets(
        session=session,
        tax_year=tax_year,
        jurisdiction=jurisdiction,
    )
    return [IncomeTaxBracketResponse.model_validate(bracket) for bracket in brackets]
