# AI 前沿日报推送工具 — 设计文档

## 概述

一个自动化工具，每天从多个信息源采集最新 AI 动态，经 AI 筛选、分类和摘要后，推送到企业微信群。通过 GitHub Actions 定时触发，无需本机运行。

## 需求

- 信息源：RSS 聚合（基础覆盖）+ 搜索 API（热点补充）
- AI 处理：Claude API 做筛选、分类、中文摘要
- 推送渠道：企业微信群机器人 Webhook
- 内容分类：产品与应用 / 开源项目 / 行业动态（不含论文）
- 定时运行：GitHub Actions schedule，每天北京时间 9:00
- 技术栈：Python

## 架构

四层流水线，每层职责单一：

```
RSS 源 + 搜索 API
       ↓
  数据采集层 (collector)
       ↓
  去重 & 预处理层 (dedup)
       ↓
  AI 处理层 (summarizer)
       ↓
  推送层 (pusher)
```

GitHub Actions 每天定时触发，从上到下执行一遍。

## 数据采集层

### RSS 源

预置高质量 AI 资讯 RSS，按类别组织：

| 类别 | 来源示例 |
|------|---------|
| 综合资讯 | Hacker News (AI 相关)、The Verge AI、TechCrunch AI |
| 开源项目 | GitHub Trending、Hugging Face Blog |
| 行业动态 | OpenAI Blog、Google AI Blog、Anthropic Blog |

RSS 源列表放在 `config.yaml` 中，用户可自行增删。使用 `feedparser` 库解析。

### 搜索 API

使用 Tavily Search API，每天用预设关键词搜索：

- `AI product launch today`
- `artificial intelligence breakthrough`
- `AI open source new release`
- `AI industry news`

关键词配置在 `config.yaml` 中，可自定义。

### 标准数据格式

```python
{
    "title": "标题",
    "url": "链接",
    "source": "来源名",
    "published": "发布时间",
    "summary": "原始摘要（如有）",
    "source_type": "rss | search"
}
```

## 去重 & 预处理层

### 两级去重

1. **URL 精确去重** — 标准化 URL（去除查询参数、尾部斜杠）后精确匹配
2. **标题模糊去重** — `difflib.SequenceMatcher` 比较标题，相似度 > 0.7 保留来源更权威的那条。阈值 0.7 偏宽松以避免漏掉改写型重复，实际使用中可根据效果调整

### 预处理

- 过滤超过 3 天的旧内容（所有时间戳统一转为 UTC 比较）
- 关键词黑名单过滤无关条目（广告、招聘等）
- 如果条目超过 80 条，按来源权威度和时间排序后截取前 80 条（控制 Claude API 输入量）
- 按发布时间排序

不引入额外依赖，用 Python 标准库实现。

## AI 处理层

单次 Claude API 调用，将去重后的全部条目（预计 30-60 条）作为 JSON 传入，要求完成：

1. **筛选** — 选出最有价值的 15-20 条
2. **分类** — 归入：产品与应用 / 开源项目 / 行业动态
3. **摘要** — 每条生成一句中文摘要，末尾生成 2-3 句「今日看点」总结

### Prompt 模板

**System prompt：**

```
你是一个专业的 AI 行业资讯编辑。你的任务是从一批原始新闻条目中筛选、分类并生成中文摘要。

规则：
- 从输入条目中选出最有价值的 15-20 条（优先选择：重大产品发布、有影响力的开源项目、重要行业事件）
- 将每条归入以下三个类别之一：产品与应用、开源项目、行业动态
- 为每条生成一句简洁的中文摘要（20-40 字）
- 最后生成 2-3 句「今日看点」总结，概括当天 AI 领域最重要的趋势
- 严格按照指定的 JSON 格式输出，不要输出任何其他内容
```

**User prompt 模板：**

```
以下是今天采集到的 AI 相关新闻条目（JSON 格式）：

{items_json}

请筛选、分类并生成中文摘要。按以下 JSON 格式输出：
{
  "categories": [
    {
      "name": "产品与应用",
      "items": [{"title": "原始标题", "summary": "中文摘要", "url": "链接"}]
    },
    {
      "name": "开源项目",
      "items": [...]
    },
    {
      "name": "行业动态",
      "items": [...]
    }
  ],
  "highlight": "今日看点：..."
}
```

### JSON 输出保障

通过预填充 assistant 消息的首字符为 `{` 来引导模型输出 JSON，同时在 prompt 中明确要求纯 JSON 输出。解析时提取响应中第一个完整 JSON 对象。如果 JSON 解析失败，重试一次；仍失败则记录错误，推送降级输出。

### 输出 JSON 格式

```json
{
  "categories": [
    {
      "name": "产品与应用",
      "items": [
        {"title": "...", "summary": "一句话中文摘要", "url": "..."}
      ]
    }
  ],
  "highlight": "今日看点：..."
}
```

模型：`claude-sonnet-4-6`，性价比最优。

## 推送层

将 Claude 返回的 JSON 格式化为 Markdown，通过企业微信 Webhook 发送。

### 消息格式

```
🤖 AI 前沿日报 2026-04-08

🚀 产品与应用
• GPT-5 发布，支持实时视频理解 (链接)
• ...

🔧 开源项目
• LLaMA 4 开源，性能追平闭源模型 (链接)
• ...

💡 行业动态
• 欧盟 AI 法案正式生效 (链接)
• ...

📌 今日看点：...
```

企业微信 Markdown 消息限制为 4096 字符。中文内容 15-20 条大概率超出限制，因此按类别拆分：每个类别作为一条独立消息发送，首条消息包含日报标题，末条消息附「今日看点」。

## 配置

```yaml
# config.yaml — 仅存放非敏感配置，提交到 git
rss_sources:
  - name: Hacker News
    url: https://hnrss.org/newest?q=AI
  - name: The Verge AI
    url: https://www.theverge.com/rss/ai-artificial-intelligence/index.xml
  # ...

search_keywords:
  - "AI product launch today"
  - "AI open source new release"
  # ...

max_items_per_category: 5
```

**敏感信息** 全部通过环境变量读取（`os.environ`），不出现在 config.yaml 中：

- `TAVILY_API_KEY` — Tavily 搜索 API 密钥
- `ANTHROPIC_API_KEY` — Claude API 密钥
- `WECHAT_WEBHOOK_URL` — 企业微信机器人 Webhook 地址

本地开发使用 `.env` 文件（已在 `.gitignore` 中），GitHub Actions 使用 Repository Secrets。

## 错误处理

每层独立处理错误，流水线尽量继续：

| 层 | 错误场景 | 处理策略 |
|----|---------|---------|
| 采集层 | 单个 RSS 源超时/不可用 | 跳过该源，记录 WARNING，继续其他源 |
| 采集层 | Tavily API 失败 | 记录 ERROR，仅用 RSS 结果继续 |
| 去重层 | 去重后条目为 0 | 记录 ERROR，推送「今日无新闻」通知，终止 |
| AI 层 | Claude API 调用失败 | 重试 1 次（间隔 10s）；仍失败则推送原始条目标题列表作为降级输出 |
| AI 层 | Claude 返回非法 JSON | 重试 1 次；仍失败则记录错误，推送降级输出 |
| AI 层 | Claude API 429 限流 | 遵循 `Retry-After` 响应头等待后重试 |
| 推送层 | Webhook 请求失败 | 重试 2 次（间隔 5s）；仍失败则记录 ERROR |

**致命错误**：采集层所有源都失败（RSS 全挂 + Tavily 也失败），终止流水线并通过 GitHub Actions 失败状态告警。

**降级输出格式**（Claude API 失败时）：

```
🤖 AI 前沿日报 2026-04-08（AI 摘要不可用，仅展示原始标题）

• 标题1 (链接)
• 标题2 (链接)
• ...
```

## 日志

使用 Python `logging` 模块，输出到 stdout（GitHub Actions 自动捕获）。

- **INFO**：每层开始/完成、条目数量、推送成功
- **WARNING**：单个源失败跳过、去重丢弃数量
- **ERROR**：API 调用失败、JSON 解析失败、推送失败

GitHub Actions job summary 中输出本次运行的简要统计：采集条目数、去重后条目数、最终推送条目数。

## 项目结构

```
ai-news-daily/
├── config.yaml            # 数据源和推送配置
├── requirements.txt       # Python 依赖
├── src/
│   ├── collector.py       # 数据采集（RSS + 搜索）
│   ├── dedup.py           # 去重 & 预处理
│   ├── summarizer.py      # Claude AI 处理
│   ├── pusher.py          # 企业微信推送
│   └── main.py            # 入口，串联流水线
├── .github/
│   └── workflows/
│       └── daily-ai-news.yml
└── .env.example           # 环境变量模板
```

## 部署

GitHub Actions 定时触发：

```yaml
# .github/workflows/daily-ai-news.yml
on:
  schedule:
    - cron: '0 1 * * *'    # UTC 01:00 = 北京时间 09:00
  workflow_dispatch:         # 支持手动触发
```

## 依赖

- `feedparser` — RSS 解析
- `anthropic` — Claude API 调用
- `tavily-python` — Tavily 搜索 API
- `requests` — HTTP 请求（企业微信 Webhook）
- `pyyaml` — 配置文件解析
