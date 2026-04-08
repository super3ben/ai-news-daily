import os
import pytest


@pytest.fixture(autouse=True)
def default_env_vars(monkeypatch):
    """Set default env vars for all tests unless explicitly overridden."""
    monkeypatch.setenv("TAVILY_API_KEY", "default_test_tavily_key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "default_test_anthropic_key")
    monkeypatch.setenv("WECHAT_WEBHOOK_URL", "https://default.example.com/webhook")
