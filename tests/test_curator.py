# tests/test_curator.py
from unittest import mock
from briefing.curator import build_prompt, curate


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


def test_curate_delegates_to_provider():
    config = {"story_count": "1", "model": "x", "api_url": "y",
              "temperature": "0.3", "timeout_seconds": "10"}
    headlines = [{"title": "News", "url": "https://x.com", "source": "BBC"}]
    provider = mock.Mock()
    provider.call.return_value = [
        {"headline": "Picked", "source": "BBC", "url": "https://x.com", "summary": "Key"},
    ]
    stories = curate(headlines, config, provider, api_key="sk-test")
    assert len(stories) == 1
    provider.call.assert_called_once()
    prompt_arg = provider.call.call_args[0][0]
    assert "BBC" in prompt_arg
