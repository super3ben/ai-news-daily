# tests/test_summarizer.py
import json
from unittest.mock import patch, MagicMock
import anthropic
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


def test_build_prompt_skips_malformed_items():
    items = [
        {"title": "Good Title", "url": "https://a.com/1"},
        {"url": "https://a.com/2"},           # missing title
        {"title": "No URL Item"},              # missing url
        {},                                    # empty dict
    ]
    _, user = build_prompt(items)
    assert "Good Title" in user
    assert "No URL Item" not in user


def test_parse_response_valid_json():
    result = parse_response(VALID_RESPONSE)
    assert "categories" in result
    assert len(result["categories"]) == 3
    assert "highlight" in result


def test_parse_response_invalid_json_returns_none():
    result = parse_response("this is not json at all")
    assert result is None


def test_parse_response_empty_string_returns_none():
    assert parse_response("") is None


def test_parse_response_extracts_embedded_json():
    wrapped = 'Some preamble {"categories": [], "highlight": "x"} trailing text'
    result = parse_response(wrapped)
    assert result is not None
    assert "categories" in result


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
    assert result is not None
    assert "categories" in result
    assert "highlight" in result


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


def test_summarize_rate_limit_does_not_sleep_on_final_attempt():
    """Sleep must not be called when the last attempt is rate-limited."""
    import httpx
    mock_httpx_response = MagicMock(spec=httpx.Response)
    mock_httpx_response.headers = {"retry-after": "5"}
    mock_httpx_response.status_code = 429
    rate_limit_err = anthropic.RateLimitError(
        "rate limited", response=mock_httpx_response, body=None
    )

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = rate_limit_err

    with patch("src.summarizer.anthropic.Anthropic", return_value=mock_client):
        with patch("src.summarizer.time.sleep") as mock_sleep:
            # max_retries=0 means only one attempt total
            result = summarize(SAMPLE_ITEMS, api_key="fake_key", max_retries=0)

    assert result is None
    mock_sleep.assert_not_called()


def test_summarize_returns_none_after_all_retries_fail():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("API error")

    with patch("src.summarizer.anthropic.Anthropic", return_value=mock_client):
        with patch("src.summarizer.time.sleep"):
            result = summarize(SAMPLE_ITEMS, api_key="fake_key")
    assert result is None
