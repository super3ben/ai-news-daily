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
