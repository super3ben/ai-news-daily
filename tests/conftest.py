import pytest


@pytest.fixture(autouse=True)
def default_env_vars(monkeypatch):
    """Provide default env vars for all tests to prevent leaking real credentials.

    Tests that need specific env var values should use monkeypatch.setenv() to override.
    Tests that need missing env vars should use monkeypatch.delenv() to remove.
    """
    monkeypatch.setenv("TAVILY_API_KEY", "default_test_tavily_key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "default_test_anthropic_key")
    monkeypatch.setenv("WECHAT_WEBHOOK_URL", "https://default.example.com/webhook")
