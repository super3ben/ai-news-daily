# src/history.py
import json
import logging
import os
from typing import Iterable

from src.dedup import normalize_url

logger = logging.getLogger(__name__)

DEFAULT_MAX_SIZE = 2000


def load_history(path: str) -> list[str]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        urls = data.get("urls", [])
        if not isinstance(urls, list):
            return []
        return urls
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load history from {path}: {e}")
        return []


def filter_new(items: list[dict], history: Iterable[str]) -> list[dict]:
    seen = set(history)
    fresh = []
    skipped = 0
    for item in items:
        url = item.get("url")
        if not url:
            continue
        if normalize_url(url) in seen:
            skipped += 1
            continue
        fresh.append(item)
    if skipped:
        logger.info(f"History filter: skipped {skipped} previously pushed items")
    return fresh


def save_history(
    path: str,
    previous: list[str],
    new_items: list[dict],
    max_size: int = DEFAULT_MAX_SIZE,
) -> None:
    existing = set(previous)
    ordered = list(previous)
    for item in new_items:
        url = item.get("url")
        if not url:
            continue
        norm = normalize_url(url)
        if norm in existing:
            continue
        existing.add(norm)
        ordered.append(norm)

    if len(ordered) > max_size:
        ordered = ordered[-max_size:]

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"urls": ordered}, f, ensure_ascii=False, indent=2)
    logger.info(f"History saved: {len(ordered)} urls at {path}")
