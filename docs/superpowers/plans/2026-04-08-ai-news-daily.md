# AI 前沿日报推送工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated daily AI news digest tool that collects, deduplicates, summarizes (via Claude), and pushes to WeChat Work group bot, triggered by GitHub Actions.

**Architecture:** Four-layer pipeline (collector → dedup → summarizer → pusher) with config-driven sources. RSS feeds provide stable coverage, Tavily search fills trending gaps. Claude API produces structured Chinese summaries. Each layer is a standalone module with clear interfaces.

**Tech Stack:** Python 3.11+, feedparser, anthropic SDK, tavily-python, requests, pyyaml

**Spec:** `docs/superpowers/specs/2026-04-08-ai-news-daily-design.md`

---

## File Structure

```
ai-news-daily/
├── config.yaml              # RSS sources, search keywords, settings
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── main.py              # Pipeline orchestrator + CLI entry point
│   ├── config.py            # Load config.yaml + env vars
│   ├── collector.py         # RSS + Tavily data collection
│   ├── dedup.py             # URL/title dedup + preprocessing
│   ├── summarizer.py        # Claude API summarization
│   └── pusher.py            # WeChat Work webhook delivery
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_collector.py
│   ├── test_dedup.py
│   ├── test_summarizer.py
│   └── test_pusher.py
└── .github/
    └── workflows/
        └── daily-ai-news.yml
```

---

### Task 1: Project Scaffolding & Config

**Files:**
- Create: `config.yaml`, `requirements.txt`, `.env.example`, `.gitignore`, `src/__init__.py`, `tests/__init__.py`
- Create: `src/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Initialize git repo and create project skeleton**

```bash
cd /Users/sunxingda/project/tools
git init
```

- [ ] **Step 2: Create requirements.txt**

```
feedparser>=6.0
anthropic>=0.40.0
tavily-python>=0.5.0
requests>=2.31.0
pyyaml>=6.0
pytest>=8.0
```

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.pyc
.env
.venv/
.pytest_cache/
```

- [ ] **Step 4: Create .env.example**

```
TAVILY_API_KEY=your_tavily_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key
```

- [ ] **Step 5: Create config.yaml**

```yaml
rss_sources:
  - name: Hacker News AI
    url: https://hnrss.org/newest?q=AI
  - name: The Verge AI
    url: https://www.theverge.com/rss/ai-artificial-intelligence/index.xml
  - name: TechCrunch AI
    url: https://techcrunch.com/category/artificial-intelligence/feed/
  - name: Hugging Face Blog
    url: https://huggingface.co/blog/feed.xml
  - name: OpenAI Blog
    url: https://openai.com/blog/rss.xml
  - name: Google AI Blog
    url: https://blog.google/technology/ai/rss/
  - name: Anthropic Blog
    url: https://www.anthropic.com/rss.xml

search_keywords:
  - "AI product launch today"
  - "artificial intelligence breakthrough"
  - "AI open source new release"
  - "AI industry news"

max_items_per_category: 5
max_age_days: 3
max_input_items: 80
dedup_similarity_threshold: 0.7
```

- [ ] **Step 6: Create empty __init__.py files**

Create `src/__init__.py` and `tests/__init__.py` as empty files.

- [ ] **Step 7: Write failing test for config loading**

```python
# tests/test_config.py
import os
import pytest
from src.config import load_config


def test_load_config_returns_rss_sources(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "rss_sources:\n"
        "  - name: Test\n"
        "    url: https://example.com/rss\n"
        "search_keywords:\n"
        '  - "AI news"\n'
        "max_items_per_category: 5\n"
    )
    config = load_config(str(config_file))
    assert len(config["rss_sources"]) == 1
    assert config["rss_sources"][0]["name"] == "Test"
    assert config["search_keywords"] == ["AI news"]
    assert config["max_items_per_category"] == 5


def test_load_config_returns_env_secrets(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("rss_sources: []\nsearch_keywords: []\n")
    monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic_key")
    monkeypatch.setenv("WECHAT_WEBHOOK_URL", "https://example.com/webhook")
    config = load_config(str(config_file))
    assert config["tavily_api_key"] == "test_tavily_key"
    assert config["anthropic_api_key"] == "test_anthropic_key"
    assert config["wechat_webhook_url"] == "https://example.com/webhook"


def test_load_config_missing_env_raises(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("rss_sources: []\nsearch_keywords: []\n")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("WECHAT_WEBHOOK_URL", raising=False)
    with pytest.raises(KeyError):
        load_config(str(config_file))
```

- [ ] **Step 8: Run tests to verify they fail**

Run: `cd /Users/sunxingda/project/tools && python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 9: Implement config.py**

```python
# src/config.py
import os
import yaml


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path) as f:
        config = yaml.safe_load(f)

    config["tavily_api_key"] = os.environ["TAVILY_API_KEY"]
    config["anthropic_api_key"] = os.environ["ANTHROPIC_API_KEY"]
    config["wechat_webhook_url"] = os.environ["WECHAT_WEBHOOK_URL"]

    config.setdefault("max_items_per_category", 5)
    config.setdefault("max_age_days", 3)
    config.setdefault("max_input_items", 80)
    config.setdefault("dedup_similarity_threshold", 0.7)

    return config
```

- [ ] **Step 10: Run tests to verify they pass**

Run: `cd /Users/sunxingda/project/tools && python -m pytest tests/test_config.py -v`
Expected: All 3 tests PASS

- [ ] **Step 11: Commit**

```bash
git add config.yaml requirements.txt .env.example .gitignore src/ tests/
git commit -m "feat: project scaffolding and config loading"
```

---

### Task 2: Data Collector (RSS + Tavily)

**Files:**
- Create: `src/collector.py`
- Test: `tests/test_collector.py`

- [ ] **Step 1: Write failing tests for RSS collector**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_collector.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement collector.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_collector.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/collector.py tests/test_collector.py
git commit -m "feat: data collector with RSS and Tavily search"
```

---

### Task 3: Dedup & Preprocessing

**Files:**
- Create: `src/dedup.py`
- Test: `tests/test_dedup.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_dedup.py -v`
Expected: FAIL

- [ ] **Step 3: Implement dedup.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_dedup.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/dedup.py tests/test_dedup.py
git commit -m "feat: dedup and preprocessing with URL normalization and title similarity"
```

---

### Task 4: Claude Summarizer

**Files:**
- Create: `src/summarizer.py`
- Test: `tests/test_summarizer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_summarizer.py
import json
from unittest.mock import patch, MagicMock
from src.summarizer import summarize, build_prompt, parse_response, build_fallback_output

SAMPLE_ITEMS = [
    {"title": "GPT-5 Released", "url": "https://a.com/1", "source": "HN", "summary": "OpenAI releases GPT-5"},
    {"title": "LLaMA 4 Open Sourced", "url": "https://b.com/2", "source": "GH", "summary": "Meta open sources LLaMA 4"},
]

VALID_RESPONSE = json.dumps({
    "categories": [
        {
            "name": "产品与应用",
            "items": [{"title": "GPT-5 Released", "summary": "OpenAI 发布 GPT-5", "url": "https://a.com/1"}]
        },
        {
            "name": "开源项目",
            "items": [{"title": "LLaMA 4 Open Sourced", "summary": "Meta 开源 LLaMA 4", "url": "https://b.com/2"}]
        },
        {
            "name": "行业动态",
            "items": []
        }
    ],
    "highlight": "今日看点：GPT-5 发布标志着多模态 AI 新时代"
})


def test_build_prompt_includes_items_json():
    system, user = build_prompt(SAMPLE_ITEMS)
    assert "AI 行业资讯编辑" in system
    assert "GPT-5 Released" in user
    assert "LLaMA 4 Open Sourced" in user


def test_parse_response_valid_json():
    result = parse_response(VALID_RESPONSE)
    assert "categories" in result
    assert len(result["categories"]) == 3
    assert "highlight" in result


def test_parse_response_invalid_json_returns_none():
    result = parse_response("this is not json at all")
    assert result is None


def test_build_fallback_output():
    result = build_fallback_output(SAMPLE_ITEMS)
    assert "GPT-5 Released" in result
    assert "https://a.com/1" in result
    assert "AI 摘要不可用" in result


def test_summarize_calls_claude_api():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=VALID_RESPONSE)]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("src.summarizer.anthropic.Anthropic", return_value=mock_client):
        result = summarize(SAMPLE_ITEMS, api_key="fake_key")
    assert result["categories"] is not None


def test_summarize_retries_on_api_failure():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=VALID_RESPONSE)]

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        Exception("API error"),
        mock_message,
    ]

    with patch("src.summarizer.anthropic.Anthropic", return_value=mock_client):
        with patch("src.summarizer.time.sleep"):
            result = summarize(SAMPLE_ITEMS, api_key="fake_key")
    assert result is not None
    assert "categories" in result


def test_summarize_returns_none_after_all_retries_fail():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("API error")

    with patch("src.summarizer.anthropic.Anthropic", return_value=mock_client):
        with patch("src.summarizer.time.sleep"):
            result = summarize(SAMPLE_ITEMS, api_key="fake_key")
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_summarizer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement summarizer.py**

```python
# src/summarizer.py
import json
import logging
import time
from datetime import date

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的 AI 行业资讯编辑。你的任务是从一批原始新闻条目中筛选、分类并生成中文摘要。

规则：
- 从输入条目中选出最有价值的 15-20 条（优先选择：重大产品发布、有影响力的开源项目、重要行业事件）
- 将每条归入以下三个类别之一：产品与应用、开源项目、行业动态
- 为每条生成一句简洁的中文摘要（20-40 字）
- 最后生成 2-3 句「今日看点」总结，概括当天 AI 领域最重要的趋势
- 严格按照指定的 JSON 格式输出，不要输出任何其他内容"""

USER_PROMPT_TEMPLATE = """以下是今天采集到的 AI 相关新闻条目（JSON 格式）：

{items_json}

请筛选、分类并生成中文摘要。按以下 JSON 格式输出：
{{
  "categories": [
    {{
      "name": "产品与应用",
      "items": [{{"title": "原始标题", "summary": "中文摘要", "url": "链接"}}]
    }},
    {{
      "name": "开源项目",
      "items": [...]
    }},
    {{
      "name": "行业动态",
      "items": [...]
    }}
  ],
  "highlight": "今日看点：..."
}}"""


def build_prompt(items: list[dict]) -> tuple[str, str]:
    items_for_prompt = [
        {"title": item["title"], "url": item["url"], "summary": item.get("summary", "")}
        for item in items
    ]
    items_json = json.dumps(items_for_prompt, ensure_ascii=False, indent=2)
    user_prompt = USER_PROMPT_TEMPLATE.format(items_json=items_json)
    return SYSTEM_PROMPT, user_prompt


def parse_response(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None


def build_fallback_output(items: list[dict]) -> str:
    today = date.today().isoformat()
    lines = [f"🤖 AI 前沿日报 {today}（AI 摘要不可用，仅展示原始标题）\n"]
    for item in items[:20]:
        lines.append(f"• {item['title']} ({item['url']})")
    return "\n".join(lines)


def summarize(items: list[dict], api_key: str, max_retries: int = 1) -> dict | None:
    system_prompt, user_prompt = build_prompt(items)
    client = anthropic.Anthropic(api_key=api_key)

    for attempt in range(max_retries + 1):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": "{"},
                ],
            )
            raw_text = "{" + message.content[0].text
            result = parse_response(raw_text)
            if result:
                logger.info("Claude summarization succeeded")
                return result
            logger.warning(f"JSON parse failed (attempt {attempt + 1})")
        except anthropic.RateLimitError as e:
            retry_after = int(e.response.headers.get("retry-after", 30))
            logger.warning(f"Rate limited, waiting {retry_after}s")
            time.sleep(retry_after)
        except Exception as e:
            logger.error(f"Claude API error (attempt {attempt + 1}): {e}")
            if attempt < max_retries:
                time.sleep(10)

    logger.error("Claude summarization failed after retries")
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_summarizer.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/summarizer.py tests/test_summarizer.py
git commit -m "feat: Claude API summarizer with retry and fallback"
```

---

### Task 5: WeChat Work Pusher

**Files:**
- Create: `src/pusher.py`
- Test: `tests/test_pusher.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_pusher.py
from datetime import date
from unittest.mock import patch, MagicMock
from src.pusher import format_message, split_messages, push_to_wechat

SAMPLE_RESULT = {
    "categories": [
        {
            "name": "产品与应用",
            "items": [
                {"title": "GPT-5", "summary": "OpenAI 发布 GPT-5，支持实时视频理解", "url": "https://a.com/1"},
            ]
        },
        {
            "name": "开源项目",
            "items": [
                {"title": "LLaMA 4", "summary": "Meta 开源 LLaMA 4 模型", "url": "https://b.com/2"},
            ]
        },
        {
            "name": "行业动态",
            "items": [
                {"title": "EU AI Act", "summary": "欧盟 AI 法案正式生效", "url": "https://c.com/3"},
            ]
        },
    ],
    "highlight": "今日看点：GPT-5 的发布标志着多模态 AI 进入新阶段",
}


def test_format_message_contains_all_categories():
    messages = format_message(SAMPLE_RESULT)
    full_text = "\n".join(messages)
    assert "产品与应用" in full_text
    assert "开源项目" in full_text
    assert "行业动态" in full_text
    assert "今日看点" in full_text
    assert "GPT-5" in full_text


def test_format_message_first_has_title():
    messages = format_message(SAMPLE_RESULT)
    assert "AI 前沿日报" in messages[0]


def test_split_messages_respects_limit():
    long_text = "x" * 5000
    parts = split_messages(long_text, max_length=4096)
    assert len(parts) >= 2
    for part in parts:
        assert len(part) <= 4096


def test_push_to_wechat_sends_request():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"errcode": 0}
    with patch("src.pusher.requests.post", return_value=mock_resp) as mock_post:
        success = push_to_wechat(["test message"], "https://example.com/webhook")
    assert success is True
    assert mock_post.call_count == 1


def test_push_to_wechat_retries_on_failure():
    fail_resp = MagicMock()
    fail_resp.status_code = 500
    fail_resp.raise_for_status.side_effect = Exception("500 error")
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.json.return_value = {"errcode": 0}
    with patch("src.pusher.requests.post", side_effect=[fail_resp, ok_resp]) as mock_post:
        with patch("src.pusher.time.sleep"):
            success = push_to_wechat(["test message"], "https://example.com/webhook")
    assert success is True
    assert mock_post.call_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pusher.py -v`
Expected: FAIL

- [ ] **Step 3: Implement pusher.py**

```python
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
        if len(current) + len(line) + 1 > max_length:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pusher.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/pusher.py tests/test_pusher.py
git commit -m "feat: WeChat Work webhook pusher with retry and message splitting"
```

---

### Task 6: Main Pipeline Orchestrator

**Files:**
- Create: `src/main.py`
- Test: `tests/test_main.py` (integration-style with mocks)

- [ ] **Step 1: Write failing test**

```python
# tests/test_main.py
import os
import pytest
from unittest.mock import patch, MagicMock
from src.main import run_pipeline


def test_run_pipeline_happy_path(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "rss_sources:\n"
        "  - name: Test\n"
        "    url: https://example.com/rss\n"
        "search_keywords:\n"
        '  - "AI news"\n'
        "max_items_per_category: 5\n"
    )
    monkeypatch.setenv("TAVILY_API_KEY", "fake")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("WECHAT_WEBHOOK_URL", "https://example.com/webhook")

    collected = [
        {"title": "News 1", "url": "https://a.com/1", "published": None, "source": "HN", "summary": "", "source_type": "rss"},
    ]
    summarized = {
        "categories": [
            {"name": "产品与应用", "items": [{"title": "News 1", "summary": "摘要", "url": "https://a.com/1"}]},
            {"name": "开源项目", "items": []},
            {"name": "行业动态", "items": []},
        ],
        "highlight": "今日看点",
    }

    with patch("src.main.collect_all", return_value=collected):
        with patch("src.main.deduplicate", return_value=collected):
            with patch("src.main.preprocess", return_value=collected):
                with patch("src.main.summarize", return_value=summarized):
                    with patch("src.main.format_message", return_value=["msg"]):
                        with patch("src.main.push_to_wechat", return_value=True) as mock_push:
                            run_pipeline(str(config_file))

    mock_push.assert_called_once()


def test_run_pipeline_fallback_on_summarize_failure(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "rss_sources: []\nsearch_keywords: []\n"
    )
    monkeypatch.setenv("TAVILY_API_KEY", "fake")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("WECHAT_WEBHOOK_URL", "https://example.com/webhook")

    collected = [
        {"title": "News 1", "url": "https://a.com/1", "published": None, "source": "HN", "summary": "", "source_type": "rss"},
    ]

    with patch("src.main.collect_all", return_value=collected):
        with patch("src.main.deduplicate", return_value=collected):
            with patch("src.main.preprocess", return_value=collected):
                with patch("src.main.summarize", return_value=None):
                    with patch("src.main.build_fallback_output", return_value="fallback msg"):
                        with patch("src.main.push_to_wechat", return_value=True) as mock_push:
                            run_pipeline(str(config_file))

    mock_push.assert_called_once_with(["fallback msg"], "https://example.com/webhook")


def test_run_pipeline_exits_on_no_items(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "rss_sources: []\nsearch_keywords: []\n"
    )
    monkeypatch.setenv("TAVILY_API_KEY", "fake")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("WECHAT_WEBHOOK_URL", "https://example.com/webhook")

    with patch("src.main.collect_all", return_value=[]):
        with pytest.raises(SystemExit):
            run_pipeline(str(config_file))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL

- [ ] **Step 3: Implement main.py**

```python
# src/main.py
import logging
import sys

from src.config import load_config
from src.collector import collect_all
from src.dedup import deduplicate, preprocess
from src.summarizer import summarize, build_fallback_output
from src.pusher import format_message, push_to_wechat

logger = logging.getLogger(__name__)


def run_pipeline(config_path: str = "config.yaml"):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("=== AI News Daily Pipeline Start ===")

    # 1. Load config
    config = load_config(config_path)

    # 2. Collect
    items = collect_all(config)
    if not items:
        logger.error("All sources failed, no items collected. Aborting.")
        sys.exit(1)

    # 3. Dedup & preprocess
    items = deduplicate(items, config.get("dedup_similarity_threshold", 0.7))
    items = preprocess(
        items,
        max_age_days=config.get("max_age_days", 3),
        max_items=config.get("max_input_items", 80),
    )
    if not items:
        logger.error("No items after dedup/preprocess")
        push_to_wechat(["今日暂无 AI 新闻更新"], config["wechat_webhook_url"])
        return

    # 4. Summarize
    result = summarize(items, config["anthropic_api_key"])

    # 5. Push
    if result:
        messages = format_message(result)
    else:
        logger.warning("Summarization failed, using fallback output")
        messages = [build_fallback_output(items)]

    success = push_to_wechat(messages, config["wechat_webhook_url"])

    # 6. Summary
    logger.info(
        f"=== Pipeline Complete === "
        f"Collected: {len(items)} | Push: {'OK' if success else 'FAILED'}"
    )


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    run_pipeline(config_file)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_main.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: main pipeline orchestrator with fallback handling"
```

---

### Task 7: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/daily-ai-news.yml`

- [ ] **Step 1: Create workflow file**

```yaml
# .github/workflows/daily-ai-news.yml
name: AI News Daily

on:
  schedule:
    - cron: '0 1 * * *'  # UTC 01:00 = Beijing 09:00
  workflow_dispatch:

jobs:
  daily-news:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run pipeline
        env:
          TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          WECHAT_WEBHOOK_URL: ${{ secrets.WECHAT_WEBHOOK_URL }}
        run: python -m src.main 2>&1 | tee output.log

      - name: Write job summary
        if: always()
        run: |
          echo "## AI News Daily Run" >> $GITHUB_STEP_SUMMARY
          grep "Pipeline Complete\|Pipeline Start\|Total collected\|ERROR" output.log >> $GITHUB_STEP_SUMMARY || echo "Pipeline did not complete" >> $GITHUB_STEP_SUMMARY
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/daily-ai-news.yml
git commit -m "feat: GitHub Actions workflow for daily schedule"
```

---

### Task 8: Final Verification & Cleanup

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Verify project structure**

```bash
find . -type f | grep -v __pycache__ | grep -v .git | sort
```

Expected output should match the file structure defined above.

- [ ] **Step 3: Final commit (if any remaining changes)**

```bash
git status
```

- [ ] **Step 4: Summary**

Print pipeline overview and remind user to:
1. Set GitHub Secrets: `TAVILY_API_KEY`, `ANTHROPIC_API_KEY`, `WECHAT_WEBHOOK_URL`
2. Push to GitHub to activate the Actions workflow
3. Test with `workflow_dispatch` before relying on the schedule
