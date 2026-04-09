# src/collector.py
import logging
from calendar import timegm
from datetime import datetime, timedelta, timezone

import requests
import feedparser
from tavily import TavilyClient

logger = logging.getLogger(__name__)


MAX_ENTRIES_PER_FEED = 30


def collect_rss(sources: list[dict]) -> list[dict]:
    items = []
    for source in sources:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:MAX_ENTRIES_PER_FEED]:
                try:
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
                except Exception as e:
                    logger.warning(f"RSS [{source['name']}] skipping malformed entry: {e}")
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


def collect_github_trending(top_n: int = 10) -> list[dict]:
    """Fetch repos with the most stars gained recently via GitHub Search API."""
    try:
        today = datetime.now(timezone.utc)
        since = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        url = "https://api.github.com/search/repositories"
        params = {
            "q": f"created:>{since} (topic:ai OR topic:llm OR topic:machine-learning OR topic:gpt OR topic:deep-learning)",
            "sort": "stars",
            "order": "desc",
            "per_page": top_n,
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        repos = []
        for repo in resp.json().get("items", []):
            repos.append({
                "name": repo["full_name"],
                "url": repo["html_url"],
                "description": repo.get("description") or "",
                "stars": repo["stargazers_count"],
                "language": repo.get("language") or "",
            })
        logger.info(f"GitHub trending: collected {len(repos)} repos")
        return repos
    except Exception as e:
        logger.warning(f"GitHub trending failed: {e}")
        return []


def collect_all(config: dict) -> list[dict]:
    rss_items = collect_rss(config["rss_sources"])
    search_items = collect_search(config["search_keywords"], config["tavily_api_key"])
    all_items = rss_items + search_items
    logger.info(f"Total collected: {len(all_items)} items (RSS: {len(rss_items)}, Search: {len(search_items)})")
    return all_items
