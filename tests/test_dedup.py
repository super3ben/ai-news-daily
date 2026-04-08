# tests/test_dedup.py
from datetime import datetime, timezone, timedelta
from src.dedup import normalize_url, deduplicate, preprocess


def test_normalize_url_strips_query_and_trailing_slash():
    assert normalize_url("https://example.com/page?ref=twitter/") == "https://example.com/page"
    assert normalize_url("https://example.com/page/") == "https://example.com/page"


def test_deduplicate_removes_exact_url_duplicates():
    items = [
        {"title": "A", "url": "https://example.com/1", "source": "X", "source_type": "rss"},
        {"title": "B", "url": "https://example.com/1", "source": "Y", "source_type": "search"},
    ]
    result = deduplicate(items, similarity_threshold=0.7)
    assert len(result) == 1


def test_deduplicate_removes_similar_titles():
    items = [
        {"title": "OpenAI launches GPT-5 with video understanding", "url": "https://a.com/1", "source": "HN", "source_type": "rss"},
        {"title": "OpenAI launches GPT-5 with video understanding capabilities", "url": "https://b.com/2", "source": "Verge", "source_type": "rss"},
    ]
    result = deduplicate(items, similarity_threshold=0.7)
    assert len(result) == 1


def test_deduplicate_keeps_different_titles():
    items = [
        {"title": "OpenAI launches GPT-5", "url": "https://a.com/1", "source": "HN", "source_type": "rss"},
        {"title": "Google releases Gemini 3", "url": "https://b.com/2", "source": "Verge", "source_type": "rss"},
    ]
    result = deduplicate(items, similarity_threshold=0.7)
    assert len(result) == 2


def test_preprocess_filters_old_items():
    now = datetime.now(timezone.utc)
    items = [
        {"title": "New", "url": "https://a.com/1", "published": now.isoformat(), "source_type": "rss"},
        {"title": "Old", "url": "https://b.com/2", "published": (now - timedelta(days=5)).isoformat(), "source_type": "rss"},
    ]
    result = preprocess(items, max_age_days=3)
    assert len(result) == 1
    assert result[0]["title"] == "New"


def test_preprocess_keeps_items_without_published_date():
    items = [
        {"title": "No date", "url": "https://a.com/1", "published": None, "source_type": "search"},
    ]
    result = preprocess(items, max_age_days=3)
    assert len(result) == 1


def test_preprocess_filters_blacklisted_items():
    items = [
        {"title": "AI hiring new engineers", "url": "https://a.com/1", "published": None, "source_type": "rss"},
        {"title": "GPT-5 Released", "url": "https://b.com/2", "published": None, "source_type": "rss"},
    ]
    result = preprocess(items, max_age_days=3)
    assert len(result) == 1
    assert result[0]["title"] == "GPT-5 Released"


def test_preprocess_caps_at_max_items():
    items = [
        {"title": f"Item {i}", "url": f"https://a.com/{i}", "published": None, "source_type": "rss"}
        for i in range(100)
    ]
    result = preprocess(items, max_age_days=3, max_items=80)
    assert len(result) == 80


def test_preprocess_filters_old_naive_datetime():
    """Naive datetime strings (no timezone) must still be age-filtered (treated as UTC)."""
    now = datetime.now(timezone.utc)
    items = [
        {
            "title": "Old Naive",
            "url": "https://a.com/1",
            "published": (now - timedelta(days=5)).replace(tzinfo=None).isoformat(),
            "source_type": "rss",
        },
    ]
    result = preprocess(items, max_age_days=3)
    assert len(result) == 0


def test_deduplicate_first_seen_wins():
    """When two items share a URL, the first item in input order is kept."""
    items = [
        {"title": "First", "url": "https://example.com/1", "source": "X", "source_type": "rss"},
        {"title": "Second", "url": "https://example.com/1", "source": "Y", "source_type": "rss"},
    ]
    result = deduplicate(items)
    assert result[0]["title"] == "First"


def test_deduplicate_skips_malformed_items():
    """Items missing url or title are skipped rather than crashing."""
    items = [
        {"title": "Valid", "url": "https://a.com/1", "source": "X", "source_type": "rss"},
        {"url": "https://b.com/1", "source": "Y", "source_type": "rss"},   # missing title
        {"title": "No URL", "source": "Z", "source_type": "rss"},           # missing url
    ]
    result = deduplicate(items)
    assert len(result) == 1
    assert result[0]["title"] == "Valid"


def test_normalize_url_strips_fragment():
    assert normalize_url("https://example.com/page#section") == "https://example.com/page"
