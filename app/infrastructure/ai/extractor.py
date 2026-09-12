from pydantic import BaseModel, Field

from app.schemas.tax_bracket import ExtractedIncomeTaxBracket


class AIExtractorNotConfiguredError(RuntimeError):
    pass


class StructuredTaxBracketExtraction(BaseModel):
    records: list[ExtractedIncomeTaxBracket] = Field(default_factory=list)
