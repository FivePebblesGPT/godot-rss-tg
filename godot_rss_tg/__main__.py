"""Run continuously, or check the feed just once with --once."""

import argparse
import logging
import time
from functools import partial

from godot_rss_tg.config import Config
from godot_rss_tg.feed import fetch_feed
from godot_rss_tg.relay import RssRelay
from godot_rss_tg.state import LinkState
from godot_rss_tg.telegram import TelegramPublisher

LOGGER = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Relay new Godot RSS links to Telegram")
    parser.add_argument("--once", action="store_true", help="Check the feed once and exit")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    try:
        config = Config.from_environment()
    except ValueError as exc:
        LOGGER.error("Invalid configuration: %s", exc)
        return 2

    with LinkState(config.state_db_path) as state:
        relay = RssRelay(
            fetch=partial(fetch_feed, config.rss_url),
            publish=TelegramPublisher(config.bot_token, config.channel_id).send,
            state=state,
            post_existing_on_start=config.post_existing_on_start,
        )

        if args.once:
            try:
                relay.poll()
            except Exception as exc:
                LOGGER.error("Feed check failed: %s", exc)
                return 1
            return 0

        LOGGER.info("Checking %s every %d seconds", config.rss_url, config.poll_interval_seconds)
        try:
            while True:
                try:
                    relay.poll()
                except Exception as exc:
                    # The next poll retries any link not yet saved in SQLite.
                    LOGGER.error("Feed check failed: %s", exc)
                time.sleep(config.poll_interval_seconds)
        except KeyboardInterrupt:
            LOGGER.info("Bot stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
