# src/pusher.py
import logging
import time
from datetime import date

import requests

logger = logging.getLogger(__name__)

CATEGORY_ICONS = {
    "产品与应用": "🚀",
    "开源项目": "🔧",
    "行业动态": "💡",
}


def format_message(result: dict) -> list[str]:
    today = date.today().isoformat()
    messages = []
    first_non_empty = True

    for category in result["categories"]:
        if not category["items"]:
            continue
        icon = CATEGORY_ICONS.get(category["name"], "📌")
        lines = []
        if first_non_empty:
            lines.append(f"🤖 AI 前沿日报 {today}\n")
            first_non_empty = False
        lines.append(f"**{icon} {category['name']}**")
        for item in category["items"]:
            lines.append(f"• {item['summary']} [{item['title']}]({item['url']})")
        messages.append("\n".join(lines))

    if result.get("highlight"):
        messages.append(f"📌 {result['highlight']}")

    return messages


def split_messages(text: str, max_length: int = 4096) -> list[str]:
    if not text:
        return []
    if len(text) <= max_length:
        return [text]
    parts = []
    lines = text.split("\n")
    current = ""
    for line in lines:
        # If a single line itself exceeds max_length, chunk it character by character
        while len(line) > max_length:
            if current:
                parts.append(current)
                current = ""
            parts.append(line[:max_length])
            line = line[max_length:]
        if len(current) + len(line) + (1 if current else 0) > max_length:
            if current:
                parts.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line
    if current:
        parts.append(current)
    return parts


def push_to_serverchan(title: str, body: str, sendkey: str, max_retries: int = 2) -> bool:
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    payload = {"title": title, "desp": body}

    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code", -1) == 0:
                logger.info("Server酱 push succeeded")
                return True
            logger.warning(f"Server酱 API error: {data}")
            if attempt < max_retries:
                time.sleep(5)
        except Exception as e:
            logger.warning(f"Push failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries:
                time.sleep(5)

    logger.error(f"Push failed after {max_retries + 1} attempts")
    return False
