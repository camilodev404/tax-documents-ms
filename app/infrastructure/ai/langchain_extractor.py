from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import SecretStr

from app.infrastructure.ai.extractor import (
    AIExtractorNotConfiguredError,
    ExtractedTaxBrackets,
    TaxDocumentExtractionError,
)

logger = logging.getLogger(__name__)


class LangChainTaxDocumentExtractor:
    def __init__(
        self,
        *,
        model: BaseChatModel | None = None,
        model_name: str | None = None,
        api_key: SecretStr | str | None = None,
        temperature: float = 0,
    ) -> None:
        self._model = model
        self._model_name = model_name
        self._api_key = api_key
        self._temperature = temperature

    def extract(self, *, text: str, source_document: str) -> ExtractedTaxBrackets:
        model = self._model or self._build_model()

        try:
            structured_model = model.with_structured_output(ExtractedTaxBrackets)
            response: Any = structured_model.invoke(
                [
                    SystemMessage(content=_SYSTEM_PROMPT),
                    HumanMessage(
                        content=(
                            f"Source document name: {source_document}\n\n"
                            "Extract the table rows from this PDF text:\n\n"
                            f"{text}"
                        )
                    ),
                ]
            )
        except Exception as exc:
            logger.exception("Tax document extraction provider failed for %s", source_document)
            raise TaxDocumentExtractionError(
                f"Tax document extraction failed for {source_document}"
            ) from exc

        return ExtractedTaxBrackets.model_validate(response)

    def _build_model(self) -> BaseChatModel:
        if self._api_key is None:
            raise AIExtractorNotConfiguredError(
                "OPENAI_API_KEY is required to run PDF ingestion with OpenAI."
            )
        if not self._model_name:
            raise AIExtractorNotConfiguredError(
                "OPENAI_MODEL is required to run PDF ingestion with OpenAI."
            )

        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise AIExtractorNotConfiguredError(
                "langchain-openai is required to run PDF ingestion with OpenAI."
            ) from exc

        secret = (
            self._api_key.get_secret_value()
            if isinstance(self._api_key, SecretStr)
            else self._api_key
        )
        return ChatOpenAI(
            api_key=secret,
            model=self._model_name,
            temperature=self._temperature,
        )


_SYSTEM_PROMPT = """
You extract income tax bracket rows from PDF text.

Return only the requested structured output.

Rules:
- Extract exclusively rows that are present in the table.
- Do not invent records, infer missing rows, or complete absent information.
- Keep the PDF record_id as source_record_id.
- Convert NO_LIMIT to null.
- Remove thousands separators before converting money amounts.
- Represent 10% as 0.10, and use that decimal-fraction convention for all rates.
- Keep currency codes exactly as three-letter uppercase codes.
- Ignore and do not output malformed text such as source/nepk? if encountered.
- Do not generate id, created_at, or source_document.
""".strip()
