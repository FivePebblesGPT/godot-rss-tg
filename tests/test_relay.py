"""Pure offline tests of feed parsing and link delivery state."""

import tempfile
import unittest
from pathlib import Path

from godot_rss_tg.feed import FeedEntry, InvalidFeedError, parse_feed
from godot_rss_tg.relay import RssRelay
from godot_rss_tg.state import LinkState


class FeedTests(unittest.TestCase):
    def test_rss_extracts_unique_valid_links(self) -> None:
        xml = b"""<?xml version="1.0"?>
        <rss version="2.0"><channel><title>Godot</title>
          <item><link>https://godotengine.org/article/second/</link></item>
          <item><link>https://godotengine.org/article/first/</link></item>
          <item><link>https://godotengine.org/article/second/</link></item>
          <item><link>javascript:alert(1)</link></item>
        </channel></rss>"""
        self.assertEqual(
            parse_feed(xml),
            [
                FeedEntry("https://godotengine.org/article/second/"),
                FeedEntry("https://godotengine.org/article/first/"),
            ],
        )

    def test_atom_links_are_supported(self) -> None:
        xml = b"""<feed xmlns="http://www.w3.org/2005/Atom">
        <entry><link rel="self" href="https://example.org/feed/1"/>
        <link rel="alternate" href="https://example.org/article/1"/></entry>
        </feed>"""
        self.assertEqual(parse_feed(xml), [FeedEntry("https://example.org/article/1")])

    def test_invalid_xml_or_format_fails(self) -> None:
        for xml in (b"<rss>", b"<html></html>", b"<rss></rss>"):
            with self.subTest(xml=xml), self.assertRaises(InvalidFeedError):
                parse_feed(xml)


class RelayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database = Path(self.directory.name) / "state.db"

    def test_initial_baseline_only_sends_new_entries_and_persists(self) -> None:
        sent: list[str] = []
        feed = [FeedEntry("https://example.org/old")]
        with LinkState(self.database) as state:
            relay = RssRelay(lambda: feed, sent.append, state)
            self.assertEqual(relay.poll(), 0)
            feed = [FeedEntry("https://example.org/new"), *feed]
            self.assertEqual(relay.poll(), 1)
            self.assertEqual(relay.poll(), 0)
        with LinkState(self.database) as state:
            relay = RssRelay(lambda: feed, sent.append, state)
            self.assertEqual(relay.poll(), 0)
        self.assertEqual(sent, ["https://example.org/new"])

    def test_explicit_backfill_posts_oldest_first(self) -> None:
        sent: list[str] = []
        feed = [FeedEntry("https://example.org/latest"), FeedEntry("https://example.org/oldest")]
        with LinkState(self.database) as state:
            relay = RssRelay(lambda: feed, sent.append, state, post_existing_on_start=True)
            self.assertEqual(relay.poll(), 2)
            self.assertEqual(relay.poll(), 0)
        self.assertEqual(sent, ["https://example.org/oldest", "https://example.org/latest"])

    def test_failed_send_is_retried_but_successes_are_remembered(self) -> None:
        sent: list[str] = []
        fail = True

        def publish(url: str) -> None:
            nonlocal fail
            if url.endswith("latest") and fail:
                fail = False
                raise RuntimeError("temporary failure")
            sent.append(url)

        feed = [FeedEntry("https://example.org/latest"), FeedEntry("https://example.org/oldest")]
        with LinkState(self.database) as state:
            relay = RssRelay(lambda: feed, publish, state, post_existing_on_start=True)
            with self.assertRaises(RuntimeError):
                relay.poll()
            self.assertEqual(relay.poll(), 1)
        self.assertEqual(sent, ["https://example.org/oldest", "https://example.org/latest"])

    def test_empty_feed_does_not_initialize_state(self) -> None:
        sent: list[str] = []
        feed: list[FeedEntry] = []
        with LinkState(self.database) as state:
            relay = RssRelay(lambda: feed, sent.append, state)
            self.assertEqual(relay.poll(), 0)
            self.assertFalse(state.initialized())
            feed.append(FeedEntry("https://example.org/old"))
            self.assertEqual(relay.poll(), 0)
            self.assertTrue(state.initialized())
        self.assertEqual(sent, [])


if __name__ == "__main__":
    unittest.main()
