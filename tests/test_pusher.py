# tests/test_pusher.py
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
