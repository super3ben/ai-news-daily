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
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")
    monkeypatch.setenv("SERVERCHAN_SENDKEY", "SCTtestkey")
    config = load_config(str(config_file))
    assert config["tavily_api_key"] == "test_tavily_key"
    assert config["gemini_api_key"] == "test_gemini_key"
    assert config["serverchan_sendkey"] == "SCTtestkey"


def test_load_config_missing_env_raises(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("rss_sources: []\nsearch_keywords: []\n")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("SERVERCHAN_SENDKEY", raising=False)
    with pytest.raises(KeyError, match="TAVILY_API_KEY"):
        load_config(str(config_file))
