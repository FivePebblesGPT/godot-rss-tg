"""Minimal Telegram Bot API client for publishing links."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class TelegramError(RuntimeError):
    """A Telegram message could not be published."""


class TelegramPublisher:
    def __init__(self, bot_token: str, channel_id: str) -> None:
        self._endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self._channel_id = channel_id

    def send(self, link: str) -> None:
        payload = json.dumps({"chat_id": self._channel_id, "text": link}).encode("utf-8")
        request = Request(
            self._endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                result = json.load(response)
        except HTTPError as exc:
            # Never expose the exception's URL: the bot token is part of it.
            raise TelegramError(f"Telegram returned HTTP {exc.code}") from None
        except URLError:
            raise TelegramError("Could not connect to Telegram") from None
        except (OSError, ValueError):
            raise TelegramError("Telegram returned an invalid response") from None

        if not isinstance(result, dict) or result.get("ok") is not True:
            raise TelegramError("Telegram did not confirm the message")
