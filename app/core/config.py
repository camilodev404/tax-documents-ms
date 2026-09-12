from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "tax-document-ms"
    database_url: str = "postgresql+psycopg://tax:tax@localhost:5432/tax_documents"
    input_dir: Path = Path("data/input")
    ai_api_key: Optional[SecretStr] = None
    ai_model_name: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
