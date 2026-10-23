"""RSS polling and publish-once logic."""

import logging
from collections.abc import Callable

from godot_rss_tg.feed import FeedEntry
from godot_rss_tg.state import LinkState

LOGGER = logging.getLogger(__name__)


class RssRelay:
    def __init__(
        self,
        fetch: Callable[[], list[FeedEntry]],
        publish: Callable[[str], None],
        state: LinkState,
        *,
        post_existing_on_start: bool = False,
    ) -> None:
        self._fetch = fetch
        self._publish = publish
        self._state = state
        self._post_existing_on_start = post_existing_on_start

    def poll(self) -> int:
        entries = self._fetch()
        if not entries:
            LOGGER.info("No valid RSS entries found; state unchanged")
            return 0

        if not self._state.initialized():
            if not self._post_existing_on_start:
                self._state.initialize([entry.url for entry in entries])
                LOGGER.info("Initialized feed baseline with %d existing entries", len(entries))
                return 0
            self._state.initialize()

        published = 0
        for entry in reversed(entries):
            if self._state.contains(entry.url):
                continue
            self._publish(entry.url)
            self._state.mark_published(entry.url)
            published += 1
            LOGGER.info("Published %s", entry.url)
        LOGGER.info("Feed checked: %d new link(s)", published)
        return published
