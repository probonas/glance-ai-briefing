# tests/test_curator.py
import json
from unittest import mock
from briefing.config import AIConfig
from briefing.curator import build_prompt, call_deepseek, curate


def test_build_prompt_includes_headlines():
    headlines = [
        {"title": "Something happened", "url": "https://example.com/1", "source": "BBC"},
        {"title": "Markets rally", "url": "https://example.com/2", "source": "Reuters"},
    ]
    prompt = build_prompt(headlines, story_count=2)
    assert "BBC" in prompt
    assert "Reuters" in prompt
    assert "Something happened" in prompt
    assert "Markets rally" in prompt
    assert "2 most globally significant" in prompt
    assert "JSON array with 2 objects" in prompt


def test_call_deepseek_parses_valid_json():
    ai_config = AIConfig(
        api_url="https://api.deepseek.com/v1/chat/completions",
        model="deepseek-chat",
        temperature=0.3,
        timeout_seconds=10,
    )
    fake_response = mock.Mock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps([
                    {"headline": "Test", "source": "BBC", "url": "https://x.com", "summary": "Important"},
                ])
            }
        }]
    }
    fake_response.raise_for_status = mock.Mock()

    with mock.patch("briefing.curator.requests.post", return_value=fake_response):
        stories = call_deepseek("test prompt", ai_config, api_key="sk-test")
        assert len(stories) == 1
        assert stories[0]["headline"] == "Test"


def test_call_deepseek_strips_markdown_fences():
    ai_config = AIConfig(
        api_url="https://api.deepseek.com/v1/chat/completions",
        model="deepseek-chat",
        temperature=0.3,
        timeout_seconds=10,
    )
    # Some models wrap JSON in ```json ... ``` fences
    fake_response = mock.Mock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "```json\n" + json.dumps([
                    {"headline": "Fenced", "source": "X", "url": "https://x.com", "summary": "Yes"},
                ]) + "\n```"
            }
        }]
    }
    fake_response.raise_for_status = mock.Mock()

    with mock.patch("briefing.curator.requests.post", return_value=fake_response):
        stories = call_deepseek("prompt", ai_config, api_key="sk-test")
        assert len(stories) == 1
        assert stories[0]["headline"] == "Fenced"


def test_curate_orchestrates_pipeline():
    """curate() is a convenience that builds prompt + calls API."""
    ai_config = AIConfig(
        api_url="https://api.deepseek.com/v1/chat/completions",
        model="deepseek-chat",
        temperature=0.3,
        timeout_seconds=10,
    )
    headlines = [
        {"title": "News", "url": "https://x.com", "source": "BBC"},
    ]
    fake_response = mock.Mock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps([
                    {"headline": "Picked", "source": "BBC", "url": "https://x.com", "summary": "Key"},
                ])
            }
        }]
    }
    fake_response.raise_for_status = mock.Mock()

    with mock.patch("briefing.curator.requests.post", return_value=fake_response):
        stories = curate(headlines, ai_config, story_count=1, api_key="sk-test")
        assert len(stories) == 1
        assert stories[0]["headline"] == "Picked"
