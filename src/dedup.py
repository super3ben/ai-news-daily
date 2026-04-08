# src/dedup.py
import logging
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

BLACKLIST_KEYWORDS = ["sponsored", "advertisement", "hiring", "job opening", "招聘", "广告"]


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def deduplicate(items: list[dict], similarity_threshold: float = 0.7) -> list[dict]:
    seen_urls: set[str] = set()
    unique_items: list[dict] = []

    for item in items:
        norm_url = normalize_url(item["url"])
        if norm_url in seen_urls:
            logger.debug(f"URL duplicate removed: {item['title']}")
            continue
        seen_urls.add(norm_url)

        is_dup = False
        for existing in unique_items:
            ratio = SequenceMatcher(None, item["title"].lower(), existing["title"].lower()).ratio()
            if ratio > similarity_threshold:
                logger.debug(f"Title duplicate removed: '{item['title']}' ~ '{existing['title']}' ({ratio:.2f})")
                is_dup = True
                break
        if not is_dup:
            unique_items.append(item)

    removed = len(items) - len(unique_items)
    if removed:
        logger.info(f"Dedup: removed {removed} duplicates, {len(unique_items)} remaining")
    return unique_items


def preprocess(
    items: list[dict],
    max_age_days: int = 3,
    max_items: int = 80,
) -> list[dict]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)
    result = []

    for item in items:
        title_lower = item.get("title", "").lower()
        if any(kw in title_lower for kw in BLACKLIST_KEYWORDS):
            logger.debug(f"Blacklisted: {item['title']}")
            continue

        if item.get("published"):
            try:
                pub = datetime.fromisoformat(item["published"])
                if pub < cutoff:
                    continue
            except (ValueError, TypeError):
                pass

        result.append(item)

    result.sort(key=lambda x: x.get("published") or "", reverse=True)

    if len(result) > max_items:
        logger.warning(f"Capping items from {len(result)} to {max_items}")
        result = result[:max_items]

    logger.info(f"Preprocess: {len(result)} items after filtering")
    return result
