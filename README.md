# Godot RSS → Telegram

A small Python 3.14 bot that checks [Godot's RSS feed](https://godotengine.org/rss.xml) and posts **new article URLs** to a Telegram channel. It uses `uv` for Python/dependency management, SQLite for deduplication, and a lightweight local systemd timer to avoid running Docker continuously. No third-party Python packages are necessary.

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy its token.
2. Add it as a **channel administrator** with **Post Messages** permission.
3. Create `.env` with your Telegram credentials:

   ```sh
   cp .env.example .env
   # Edit TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID.
   ```

   Public channels use `@your_channel`; private channels normally use an ID starting with `-100`.

## Local systemd timer (recommended)

**Linux requirements:** systemd user services, Bash, curl, `flock`, `sha256sum`, Docker Engine and the Docker Compose plugin. Your user must have access to the Docker daemon. You only need `uv` in the container.

From the repository root:

```sh
docker compose build bot
bash scripts/install-systemd-user.sh
```

The installer symlinks the launcher to `~/.local/bin/godot-rss-tg-check`, installs two systemd **user** units, and enables the timer. The units do not require the repository to be in a particular directory. If you move the repository, rerun the installer.

The timer checks the RSS feed **hourly all day** and **every 15 minutes between 14:00 and 18:00 Europe/Berlin time** (CET or CEST depending on daylight saving). The afternoon peak is a scheduling preference, not a guarantee that Godot only publishes during those hours. Adjust `systemd/godot-rss-tg.timer` and rerun the installer if desired.

Each check downloads the feed to a temporary file and compares its SHA-256 hash with the last **successfully processed** feed. If nothing changed, **Docker never starts**. On a change, it runs a one-shot container (`docker compose run --rm`), lets the Python bot publish new links, then exits. If the bot fails, the fingerprint is **not** advanced so the next timer checks again. Occasional RSS metadata-only changes can start the container harmlessly: SQLite prevents already-seen URLs from being posted again.

Useful commands:

```sh
systemctl --user list-timers godot-rss-tg.timer
systemctl --user start godot-rss-tg.service  # Check now (skips unchanged feeds)
journalctl --user -u godot-rss-tg.service -n 50 --no-pager
bash scripts/check-rss.sh --force           # Run the bot even when RSS is unchanged
systemctl --user disable --now godot-rss-tg.timer
```

`--force` also runs the bot when the RSS hash is unchanged; it does **not** bypass SQLite deduplication. To keep a user timer active when logged out, your host may need `sudo loginctl enable-linger "$USER"` once. Running a systemd user service requires an active Docker daemon; make sure Docker is started on your host.

The host-side checker uses `https://godotengine.org/rss.xml` by default. Set the `RSS_URL` environment variable for the **service** if you need a different URL; the same URL is forwarded into Docker so host and container always check the same feed. Telegram credentials are read inside the container from `.env` and are not sourced or evaluated by the host shell.

## Manual one-shot run

To check immediately without the timer:

```sh
docker compose build bot
docker compose run --rm --no-deps bot
```

The container exits when the check finishes. **Do not use `docker compose up -d` as a polling daemon**: the Compose service now runs once and has no restart policy.

The first successful check **records existing feed entries without posting** them. This prevents a backlog of old posts. Afterward, new entries publish oldest first. To post all currently visible entries on the very first run instead, set `POST_EXISTING_ON_START=true` in `.env` **before initializing the SQLite volume**.

## Local Python development

```sh
uv python install 3.14
uv sync --locked
uv run --locked --env-file .env python -m godot_rss_tg --once
uv run --locked python -m unittest discover -s tests -v
bash tests/test-check-rss.sh
```

Running `uv run --locked --env-file .env python -m godot_rss_tg` (without `--once`) still supports continuous polling for development, using `POLL_INTERVAL_SECONDS`.

## Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather (required in `.env`) | — |
| `TELEGRAM_CHANNEL_ID` | `@channel` or numeric ID (required in `.env`) | — |
| `RSS_URL` | RSS URL, set on the host for the systemd checker | `https://godotengine.org/rss.xml` |
| `POLL_INTERVAL_SECONDS` | Continuous-mode polling interval only | `900` |
| `STATE_DB_PATH` | SQLite deduplication file | `./data/seen.sqlite3` locally; `/data/seen.sqlite3` in Compose |
| `POST_EXISTING_ON_START` | Publish existing feed entries on first successful run | `false` |
| `XDG_STATE_HOME` | Optional host location for feed fingerprints | `$HOME/.local/state` |

## Reliability and deployment notes

- The Compose volume `bot-data` persists SQLite state even though one-shot containers are removed. Do **not** delete this volume to avoid losing the already-posted history.
- The host fingerprint lives in `~/.local/state/godot-rss-tg/last-successful-sha256` by default. Removing it forces the next timer run to start the container, while SQLite still prevents duplicates.
- When Telegram sends a message successfully, its URL is saved in SQLite. A crash after sending but before committing can exceptionally cause a duplicate because `sendMessage` offers no idempotency key.
- `flock` prevents overlapping host-side checks. Don't also run a separate always-on instance of the same bot using the same channel and SQLite database.
- RSS feeds generally expose only a finite number of recent posts. With hourly checks outside peak hours, very short-lived feed items could theoretically be missed; adjust the timer if you need a stricter delivery window.
- The container has no inbound ports, runs as a non-root user, and uses a read-only root filesystem. The host user must have trusted Docker access.