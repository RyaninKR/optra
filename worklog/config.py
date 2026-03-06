from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # OAuth app credentials (for `worklog auth` flow)
    slack_client_id: str = ""
    slack_client_secret: str = ""
    notion_client_id: str = ""
    notion_client_secret: str = ""

    # Direct tokens (fallback if OAuth not used)
    slack_bot_token: str = ""
    notion_token: str = ""

    anthropic_api_key: str = ""
    db_path: Path = Path("worklog.db")


settings = Settings()


def get_slack_token() -> Optional[str]:
    """Resolve Slack token: credential store first, then .env fallback."""
    from worklog.auth.store import get_token

    return get_token("slack") or settings.slack_bot_token or None


def get_notion_token() -> Optional[str]:
    """Resolve Notion token: credential store first, then .env fallback."""
    from worklog.auth.store import get_token

    return get_token("notion") or settings.notion_token or None
