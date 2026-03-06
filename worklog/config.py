from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    slack_bot_token: str = ""
    notion_token: str = ""
    anthropic_api_key: str = ""

    db_path: Path = Path("worklog.db")


settings = Settings()
