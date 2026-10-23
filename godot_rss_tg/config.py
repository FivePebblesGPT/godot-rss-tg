"""Configuration loaded from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Config:
    bot_token: str
    channel_id: str
    rss_url: str
    poll_interval_seconds: int
    state_db_path: Path
    post_existing_on_start: bool

    @classmethod
    def from_environment(cls) -> "Config":
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        channel_id = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()
        rss_url = os.getenv("RSS_URL", "https://godotengine.org/rss.xml").strip()

        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN must be set")
        if not channel_id:
            raise ValueError("TELEGRAM_CHANNEL_ID must be set")
        if not rss_url.startswith(("https://", "http://")):
            raise ValueError("RSS_URL must be an HTTP(S) URL")

        try:
            interval = int(os.getenv("POLL_INTERVAL_SECONDS", "900"))
        except ValueError as exc:
            raise ValueError("POLL_INTERVAL_SECONDS must be an integer") from exc
        if interval < 60:
            raise ValueError("POLL_INTERVAL_SECONDS must be at least 60")

        initial = os.getenv("POST_EXISTING_ON_START", "false").lower().strip()
        if initial not in {"true", "false"}:
            raise ValueError("POST_EXISTING_ON_START must be true or false")

        return cls(
            bot_token=bot_token,
            channel_id=channel_id,
            rss_url=rss_url,
            poll_interval_seconds=interval,
            state_db_path=Path(os.getenv("STATE_DB_PATH", "./data/seen.sqlite3")),
            post_existing_on_start=(initial == "true"),
        )
