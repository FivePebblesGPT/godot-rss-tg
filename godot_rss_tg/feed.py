"""Fetch and parse RSS 2.0 or Atom feeds without external dependencies."""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

LOGGER = logging.getLogger(__name__)
ATOM_NS = "{http://www.w3.org/2005/Atom}"


class InvalidFeedError(ValueError):
    """Raised when an XML document is not a supported feed."""


@dataclass(frozen=True, slots=True)
class FeedEntry:
    url: str


def _valid_link(value: str | None) -> str | None:
    link = (value or "").strip()
    parsed = urlsplit(link)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return link


def parse_feed(xml: bytes) -> list[FeedEntry]:
    """Extract unique article URLs in feed order (typically newest first)."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise InvalidFeedError("RSS feed is not valid XML") from exc

    candidates: list[str | None]
    if root.tag == "rss":
        channel = root.find("channel")
        if channel is None:
            raise InvalidFeedError("RSS feed has no channel")
        candidates = [item.findtext("link") for item in channel.findall("item")]
    elif root.tag == f"{ATOM_NS}feed":
        candidates = []
        for entry in root.findall(f"{ATOM_NS}entry"):
            links = entry.findall(f"{ATOM_NS}link")
            article = next(
                (link.get("href") for link in links if link.get("rel", "alternate") == "alternate"),
                None,
            )
            candidates.append(article)
    else:
        raise InvalidFeedError("Unsupported feed format (expected RSS or Atom)")

    seen: set[str] = set()
    entries: list[FeedEntry] = []
    for candidate in candidates:
        url = _valid_link(candidate)
        if url is None:
            LOGGER.warning("Skipping feed entry without a valid HTTP(S) link")
            continue
        if url not in seen:
            entries.append(FeedEntry(url))
            seen.add(url)
    return entries


def fetch_feed(url: str) -> list[FeedEntry]:
    request = Request(url, headers={"User-Agent": "godot-rss-tg/0.1 (+RSS reader)"})
    with urlopen(request, timeout=20) as response:
        xml = response.read(10 * 1024 * 1024 + 1)
    if len(xml) > 10 * 1024 * 1024:
        raise InvalidFeedError("RSS feed exceeds 10 MiB")
    return parse_feed(xml)
