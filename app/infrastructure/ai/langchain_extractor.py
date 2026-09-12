from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import SecretStr

from app.infrastructure.ai.extractor import (
    AIExtractorNotConfiguredError,
    StructuredTaxBracketExtraction,
)
from app.schemas.tax_bracket import ExtractedIncomeTaxBracket
from app.services.tax_document_extractor import PdfDocument


class LangChainTaxDocumentExtractor:
    def __init__(
        self,
        *,
        model: BaseChatModel | None = None,
        model_name: str | None = None,
        api_key: SecretStr | str | None = None,
    ) -> None:
        self._model = model
        self._model_name = model_name
        self._api_key = api_key

    def extract(self, document: PdfDocument) -> list[ExtractedIncomeTaxBracket]:
        if self._model is None:
            raise AIExtractorNotConfiguredError(
                "LangChain extractor is a placeholder. TODO: configure a concrete provider "
                "and model, then inject a BaseChatModel. No extraction is attempted without it."
            )

        structured_model = self._model.with_structured_output(StructuredTaxBracketExtraction)
        response: Any = structured_model.invoke(
            [
                SystemMessage(
                    content=(
                        "Extract income tax bracket rows from the PDF content. "
                        "Return structured records only. Do not infer missing rows."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Source document: {document.filename}\n"
                        "TODO: replace this placeholder with parsed PDF text before "
                        "invoking the LLM.\n"
                        f"Raw PDF byte length: {len(document.content)}"
                    )
                ),
            ]
        )

        extraction = StructuredTaxBracketExtraction.model_validate(response)
        return extraction.records
