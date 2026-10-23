# Godot RSS → Telegram

A small Python 3.14 bot that polls [Godot's RSS feed](https://godotengine.org/rss.xml) and posts **new article links** to a Telegram channel. It uses `uv` for Python/dependency management, SQLite for deduplication, and Docker Compose for running continuously. No third-party Python packages are necessary.

## Setup

1. Create a Telegram bot through [@BotFather](https://t.me/BotFather) and copy its token.
2. Add the bot as an **administrator** of the target Telegram channel, with **Post Messages** permission.
3. Create a local config file and edit `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHANNEL_ID`:

   ```sh
   cp .env.example .env
   ```

   For a public channel, use `@your_channel`. For a private channel, use its numeric chat ID (normally starting with `-100`).

4. Start it with Docker Compose:

   ```sh
   docker compose up -d --build
   docker compose logs -f bot
   ```

The initial check **records existing feed entries without posting** them, preventing a backlog of old articles. Later checks publish new links, oldest first, at a default interval of 15 minutes. To post all articles currently in the feed on first startup instead, set `POST_EXISTING_ON_START=true` **before the first run**. This setting is ignored after the SQLite database has been initialized. The bot posts just the URL, allowing Telegram to create a link preview.

## Local development

Install [uv](https://docs.astral.sh/uv/), then:

```sh
cp .env.example .env
# edit .env
uv python install 3.14
uv sync --locked
uv run --locked --env-file .env python -m godot_rss_tg --once
uv run --locked --env-file .env python -m godot_rss_tg
```

`--once` checks the feed exactly once and exits (exit status 1 if checking or posting failed). The continuous command retries a failed check at the next poll. The `.env` file is excluded from Git.

Run the offline tests:

```sh
uv run --locked python -m unittest discover -s tests -v
```

## Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather (**required**) | — |
| `TELEGRAM_CHANNEL_ID` | `@channel` or numeric channel ID (**required**) | — |
| `RSS_URL` | RSS or Atom feed URL | `https://godotengine.org/rss.xml` |
| `POLL_INTERVAL_SECONDS` | Poll interval, minimum 60 seconds | `900` |
| `STATE_DB_PATH` | SQLite file for published URLs | `./data/seen.sqlite3` locally, `/data/seen.sqlite3` in Compose |
| `POST_EXISTING_ON_START` | `true` to post current entries on first run | `false` |

## Reliability and deployment notes

- Successfully posted URLs are committed to SQLite one by one, so the next poll skips them even across restarts. A failure during an individual send stops that check; remaining links are retried at the next interval.
- On the very first successful check, a baseline is recorded so existing feed articles aren't posted as new. Keep the `bot-data` Docker volume: deleting it resets that baseline.
- There is a small possibility of a duplicate if Telegram accepts a message but the process stops before SQLite records it; the Telegram API does not provide an idempotency key for `sendMessage`.
- Run **one instance** of this bot per state database/channel, not multiple replicas.
- The container has no inbound ports, runs as non-root, and retains state in a named Docker volume.
