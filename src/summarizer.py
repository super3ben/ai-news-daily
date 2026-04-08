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
            response_text = message.content[0].text
            # The assistant prefill was "{", so the response continues from there.
            # Try with prefill prepended first; fall back to raw text if that fails.
            result = parse_response("{" + response_text) or parse_response(response_text)
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
