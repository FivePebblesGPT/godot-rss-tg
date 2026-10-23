"""Durable deduplication state for published links."""

import sqlite3
from pathlib import Path
from types import TracebackType


class LinkState:
    def __init__(self, database: Path) -> None:
        database.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(database, timeout=5)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS seen_links "
            "(url TEXT PRIMARY KEY, posted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS settings "
            "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self._db.commit()

    def __enter__(self) -> "LinkState":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._db.close()

    def initialized(self) -> bool:
        row = self._db.execute("SELECT 1 FROM settings WHERE key = 'initialized'").fetchone()
        return row is not None

    def initialize(self, existing_links: list[str] | None = None) -> None:
        # Only commit the baseline and initialized flag together.
        with self._db:
            self._db.executemany(
                "INSERT OR IGNORE INTO seen_links (url) VALUES (?)",
                ((url,) for url in (existing_links or [])),
            )
            self._db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('initialized', '1')"
            )

    def contains(self, url: str) -> bool:
        row = self._db.execute("SELECT 1 FROM seen_links WHERE url = ?", (url,)).fetchone()
        return row is not None

    def mark_published(self, url: str) -> None:
        with self._db:
            self._db.execute("INSERT OR IGNORE INTO seen_links (url) VALUES (?)", (url,))
