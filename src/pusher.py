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

    for i, category in enumerate(result["categories"]):
        if not category["items"]:
            continue
        icon = CATEGORY_ICONS.get(category["name"], "📌")
        lines = []
        if i == 0:
            lines.append(f"🤖 AI 前沿日报 {today}\n")
        lines.append(f"**{icon} {category['name']}**")
        for item in category["items"]:
            lines.append(f"• {item['summary']} [{item['title']}]({item['url']})")
        messages.append("\n".join(lines))

    if result.get("highlight"):
        messages.append(f"📌 {result['highlight']}")

    return messages


def split_messages(text: str, max_length: int = 4096) -> list[str]:
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


def push_to_wechat(messages: list[str], webhook_url: str, max_retries: int = 2) -> bool:
    all_success = True
    for msg in messages:
        parts = split_messages(msg)
        for part in parts:
            payload = {
                "msgtype": "markdown",
                "markdown": {"content": part},
            }
            success = False
            for attempt in range(max_retries + 1):
                try:
                    resp = requests.post(webhook_url, json=payload, timeout=10)
                    resp.raise_for_status()
                    data = resp.json()
                    if data.get("errcode", 0) == 0:
                        success = True
                        break
                    logger.warning(f"WeChat API error: {data}")
                except Exception as e:
                    logger.warning(f"Push failed (attempt {attempt + 1}): {e}")
                    if attempt < max_retries:
                        time.sleep(5)
            if not success:
                logger.error(f"Push failed after {max_retries + 1} attempts")
                all_success = False
    return all_success
