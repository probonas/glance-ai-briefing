# tests/test_providers.py
import json
from unittest import mock
import pytest
from briefing.providers import get_provider
from briefing.providers.deepseek import DeepSeekProvider
from briefing.providers.google import GoogleProvider
from briefing.providers.base import _call_openai_compatible


def test_call_openai_compatible_parses_json_array():
    config = {
        "api_url": "https://example.com/v1/chat/completions",
        "model": "test-model",
        "temperature": "0.3",
        "timeout_seconds": "10",
    }
    fake_response = mock.Mock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps([
            {"headline": "Test", "source": "BBC", "url": "https://x.com", "summary": "Important"},
        ])}}]
    }
    fake_response.raise_for_status = mock.Mock()

    with mock.patch("briefing.providers.base.requests.post", return_value=fake_response) as post:
        stories = _call_openai_compatible("prompt", config, api_key="sk-test")
        assert len(stories) == 1
        assert stories[0]["headline"] == "Test"
        post.assert_called_once()
        call_kwargs = post.call_args
        assert call_kwargs[0][0] == config["api_url"]
        assert call_kwargs[1]["headers"]["Authorization"] == "Bearer sk-test"


def test_call_openai_compatible_strips_markdown_fences():
    config = {
        "api_url": "https://example.com/v1/chat/completions",
        "model": "test-model",
        "temperature": "0.3",
        "timeout_seconds": "10",
    }
    fake_response = mock.Mock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": "```json\n" + json.dumps([
            {"headline": "Fenced", "source": "X", "url": "https://x.com", "summary": "Yes"},
        ]) + "\n```"}}]
    }
    fake_response.raise_for_status = mock.Mock()

    with mock.patch("briefing.providers.base.requests.post", return_value=fake_response):
        stories = _call_openai_compatible("prompt", config, api_key="sk-test")
        assert stories[0]["headline"] == "Fenced"


def test_get_provider_deepseek():
    provider = get_provider("deepseek")
    assert isinstance(provider, DeepSeekProvider)
    assert provider.name == "deepseek"
    assert provider.api_key_env == "DEEPSEEK_API_KEY"
    assert provider.default_model == "deepseek-chat"


def test_get_provider_google():
    provider = get_provider("google")
    assert isinstance(provider, GoogleProvider)
    assert provider.name == "google"
    assert provider.api_key_env == "GOOGLE_AI_API_KEY"
    assert provider.default_model == "gemini-2.5-flash"
    assert "generativelanguage.googleapis.com" in provider.default_api_url


def test_get_provider_unknown_raises():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_provider("openai")


def test_deepseek_provider_call_delegates_to_helper():
    provider = DeepSeekProvider()
    config = {
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "temperature": "0.3",
        "timeout_seconds": "10",
    }
    with mock.patch("briefing.providers.deepseek._call_openai_compatible", return_value=[]) as helper:
        provider.call("prompt", config, "sk-test")
        helper.assert_called_once_with("prompt", config, "sk-test")
