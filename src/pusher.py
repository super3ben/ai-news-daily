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


def format_message(result: dict, trending_repos: list[dict] | None = None) -> list[str]:
    today = date.today().isoformat()
    lines = [f"# 🤖 AI 前沿日报 {today}", ""]

    for category in result["categories"]:
        if not category["items"]:
            continue
        icon = CATEGORY_ICONS.get(category["name"], "📌")
        lines.append(f"## {icon} {category['name']}")
        lines.append("")
        for item in category["items"]:
            lines.append(f"### [{item['title']}]({item['url']})")
            lines.append("")
            lines.append(item["summary"])
            lines.append("")
            lines.append("---")
            lines.append("")

    if trending_repos:
        lines.append("## ⭐ GitHub 本周飙升项目")
        lines.append("")
        for repo in trending_repos:
            stars = repo.get("stars", 0)
            lines.append(f"### [{repo['name']}]({repo['url']})  ⭐ {stars}")
            lines.append("")
            lines.append(repo["summary"])
            lines.append("")
            lines.append("---")
            lines.append("")

    if result.get("highlight"):
        lines.append(f"## 📌 今日看点")
        lines.append("")
        lines.append(result["highlight"])

    return ["\n".join(lines)]


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


def push_to_serverchan(
    title: str, body: str, sendkey: str, api_url: str = "https://sctapi.ftqq.com", max_retries: int = 2
) -> bool:
    url = f"{api_url}/{sendkey}.send"
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
