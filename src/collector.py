# src/collector.py
import logging
from calendar import timegm
from datetime import datetime, timezone

import feedparser
from tavily import TavilyClient

logger = logging.getLogger(__name__)


def collect_rss(sources: list[dict]) -> list[dict]:
    items = []
    for source in sources:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime.fromtimestamp(
                        timegm(entry.published_parsed), tz=timezone.utc
                    ).isoformat()
                items.append({
                    "title": entry.title,
                    "url": entry.link,
                    "source": source["name"],
                    "published": published,
                    "summary": entry.get("summary", ""),
                    "source_type": "rss",
                })
            logger.info(f"RSS [{source['name']}]: collected {len(feed.entries)} entries")
        except Exception as e:
            logger.warning(f"RSS [{source['name']}] failed: {e}")
    return items


def collect_search(keywords: list[str], api_key: str) -> list[dict]:
    items = []
    try:
        client = TavilyClient(api_key=api_key)
        for keyword in keywords:
            try:
                response = client.search(keyword, max_results=10)
                for result in response.get("results", []):
                    items.append({
                        "title": result["title"],
                        "url": result["url"],
                        "source": "Tavily Search",
                        "published": None,
                        "summary": result.get("content", ""),
                        "source_type": "search",
                    })
                logger.info(f"Search [{keyword}]: collected {len(response.get('results', []))} results")
            except Exception as e:
                logger.warning(f"Search [{keyword}] failed: {e}")
    except Exception as e:
        logger.error(f"Tavily client init failed: {e}")
    return items


def collect_all(config: dict) -> list[dict]:
    rss_items = collect_rss(config["rss_sources"])
    search_items = collect_search(config["search_keywords"], config["tavily_api_key"])
    all_items = rss_items + search_items
    logger.info(f"Total collected: {len(all_items)} items (RSS: {len(rss_items)}, Search: {len(search_items)})")
    return all_items
