# tests/test_collector.py
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from src.collector import collect_rss, collect_search, collect_all


def _make_feed_entry(title, link, published_parsed=None):
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.get.return_value = ""
    if published_parsed is None:
        published_parsed = (2026, 4, 8, 10, 0, 0, 0, 0, 0)
    entry.published_parsed = published_parsed
    return entry


def test_collect_rss_returns_standard_items():
    sources = [{"name": "TestFeed", "url": "https://example.com/rss"}]
    feed = MagicMock()
    feed.entries = [_make_feed_entry("Test Title", "https://example.com/1")]
    with patch("src.collector.feedparser.parse", return_value=feed):
        items = collect_rss(sources)
    assert len(items) == 1
    assert items[0]["title"] == "Test Title"
    assert items[0]["url"] == "https://example.com/1"
    assert items[0]["source"] == "TestFeed"
    assert items[0]["source_type"] == "rss"


def test_collect_rss_returns_empty_for_empty_feed():
    sources = [{"name": "EmptyFeed", "url": "https://example.com/rss"}]
    feed = MagicMock()
    feed.entries = []
    with patch("src.collector.feedparser.parse", return_value=feed):
        items = collect_rss(sources)
    assert items == []


def test_collect_rss_handles_parse_exception():
    sources = [{"name": "BadFeed", "url": "https://bad.example.com/rss"}]
    with patch("src.collector.feedparser.parse", side_effect=Exception("timeout")):
        items = collect_rss(sources)
    assert items == []


def test_collect_search_returns_standard_items():
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {"title": "Search Hit", "url": "https://example.com/2", "content": "desc"}
        ]
    }
    with patch("src.collector.TavilyClient", return_value=mock_client):
        items = collect_search(["AI news"], api_key="fake_key")
    assert len(items) == 1
    assert items[0]["title"] == "Search Hit"
    assert items[0]["source_type"] == "search"


def test_collect_search_returns_empty_on_failure():
    with patch("src.collector.TavilyClient", side_effect=Exception("API error")):
        items = collect_search(["AI news"], api_key="fake_key")
    assert items == []


def test_collect_all_merges_rss_and_search():
    config = {
        "rss_sources": [{"name": "Feed1", "url": "https://example.com/rss"}],
        "search_keywords": ["AI news"],
        "tavily_api_key": "fake",
    }
    with patch("src.collector.collect_rss", return_value=[{"title": "RSS Item"}]):
        with patch("src.collector.collect_search", return_value=[{"title": "Search Item"}]):
            items = collect_all(config)
    assert len(items) == 2
