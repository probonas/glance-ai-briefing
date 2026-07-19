# Google AI Studio Provider Support — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Google AI Studio (Gemini) as a second LLM provider alongside DeepSeek, selected via `LLM_PROVIDER` env var with a modular provider abstraction.

**Architecture:** Separate provider modules (`deepseek.py`, `google.py`) implementing a shared `LLMProvider` protocol. Both use OpenAI-compatible chat completions via a shared HTTP helper in `base.py`. Startup resolves provider + API key; `curate()` delegates to the active provider.

**Tech Stack:** Python 3.10+, requests, pytest. No new dependencies.

## Global Constraints

- Provider selection via `LLM_PROVIDER` env var only (default: `deepseek`; valid: `deepseek`, `google`)
- Only the active provider's API key required (`DEEPSEEK_API_KEY` or `GOOGLE_AI_API_KEY`)
- Google default model: `gemini-2.5-flash`
- Google default api_url: `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`
- Remove `provider` from Glance query-param defaults
- No Google native SDK — OpenAI-compatible endpoint only

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/briefing/providers/base.py` | Create | Protocol + shared `_call_openai_compatible()` |
| `src/briefing/providers/deepseek.py` | Create | DeepSeek provider constants + `call()` |
| `src/briefing/providers/google.py` | Create | Google provider constants + `call()` |
| `src/briefing/providers/__init__.py` | Create | Provider registry + `get_provider()` |
| `src/briefing/config.py` | Modify | Remove `provider`/`model`/`api_url` from DEFAULTS; add `resolve_provider()`, `apply_provider_defaults()` |
| `src/briefing/curator.py` | Modify | Remove `call_deepseek()`; `curate()` takes provider |
| `src/briefing/cli.py` | Modify | Use `resolve_provider()` at startup |
| `src/briefing/server.py` | Modify | Accept provider; pass to `curate()` |
| `tests/test_providers.py` | Create | Provider factory + HTTP call tests |
| `tests/test_config.py` | Modify | Update defaults tests; add provider resolution tests |
| `tests/test_curator.py` | Modify | Pass provider mock to `curate()` |
| `tests/test_server.py` | Modify | Pass provider to `BriefingServer` |
| `.env.example` | Modify | Add `LLM_PROVIDER`, `GOOGLE_AI_API_KEY` |
| `docker-compose.yml` | Modify | Pass new env vars |
| `Dockerfile` | Modify | Document new env vars |
| `README.md` | Modify | Document both providers |

---

### Task 1: Provider base module + shared HTTP helper

**Files:**
- Create: `src/briefing/providers/__init__.py` (empty stub)
- Create: `src/briefing/providers/base.py`
- Test: `tests/test_providers.py`

**Interfaces:**
- Produces: `_call_openai_compatible(prompt, config, api_key) -> list[dict]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_providers.py
import json
from unittest import mock
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_providers.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# src/briefing/providers/base.py
"""Shared LLM provider protocol and OpenAI-compatible HTTP helper."""

import json
from typing import Protocol

import requests


class LLMProvider(Protocol):
    name: str
    api_key_env: str
    default_model: str
    default_api_url: str

    def call(self, prompt: str, config: dict[str, str], api_key: str) -> list[dict]:
        ...


def _call_openai_compatible(
    prompt: str, config: dict[str, str], api_key: str
) -> list[dict]:
    response = requests.post(
        config["api_url"],
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": config["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(config["temperature"]),
        },
        timeout=int(config["timeout_seconds"]),
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"].strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    parsed = json.loads(content.strip())
    if not isinstance(parsed, list):
        raise ValueError(f"LLM returned {type(parsed)}, expected list")
    return parsed
```

```python
# src/briefing/providers/__init__.py
"""LLM provider registry."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_providers.py -v`
Expected: PASS (2 tests)

---

### Task 2: DeepSeek and Google provider implementations + factory

**Files:**
- Create: `src/briefing/providers/deepseek.py`
- Create: `src/briefing/providers/google.py`
- Modify: `src/briefing/providers/__init__.py`
- Test: `tests/test_providers.py`

**Interfaces:**
- Consumes: `_call_openai_compatible()` from Task 1
- Produces: `get_provider(name: str) -> LLMProvider`, `DeepSeekProvider`, `GoogleProvider`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_providers.py
from briefing.providers import get_provider
from briefing.providers.deepseek import DeepSeekProvider
from briefing.providers.google import GoogleProvider


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
    import pytest
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
    with mock.patch("briefing.providers.base._call_openai_compatible", return_value=[]) as helper:
        provider.call("prompt", config, "sk-test")
        helper.assert_called_once_with("prompt", config, "sk-test")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_providers.py::test_get_provider_deepseek -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/briefing/providers/deepseek.py
from dataclasses import dataclass
from briefing.providers.base import _call_openai_compatible


@dataclass(frozen=True)
class DeepSeekProvider:
    name: str = "deepseek"
    api_key_env: str = "DEEPSEEK_API_KEY"
    default_model: str = "deepseek-chat"
    default_api_url: str = "https://api.deepseek.com/v1/chat/completions"

    def call(self, prompt: str, config: dict[str, str], api_key: str) -> list[dict]:
        return _call_openai_compatible(prompt, config, api_key)
```

```python
# src/briefing/providers/google.py
from dataclasses import dataclass
from briefing.providers.base import _call_openai_compatible


@dataclass(frozen=True)
class GoogleProvider:
    name: str = "google"
    api_key_env: str = "GOOGLE_AI_API_KEY"
    default_model: str = "gemini-2.5-flash"
    default_api_url: str = (
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    )

    def call(self, prompt: str, config: dict[str, str], api_key: str) -> list[dict]:
        return _call_openai_compatible(prompt, config, api_key)
```

```python
# src/briefing/providers/__init__.py
from briefing.providers.base import LLMProvider
from briefing.providers.deepseek import DeepSeekProvider
from briefing.providers.google import GoogleProvider

PROVIDERS: dict[str, LLMProvider] = {
    "deepseek": DeepSeekProvider(),
    "google": GoogleProvider(),
}


def get_provider(name: str) -> LLMProvider:
    try:
        return PROVIDERS[name]
    except KeyError:
        valid = ", ".join(sorted(PROVIDERS))
        raise ValueError(f"Unknown LLM provider {name!r}. Valid providers: {valid}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_providers.py -v`
Expected: PASS (6 tests)

---

### Task 3: Config — provider resolution and defaults

**Files:**
- Modify: `src/briefing/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `get_provider()` from Task 2
- Produces: `resolve_provider() -> tuple[LLMProvider, str]`, `apply_provider_defaults(config, provider) -> dict[str, str]`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_config.py
import pytest
from briefing.config import resolve_provider, apply_provider_defaults, parse_query_params
from briefing.providers.deepseek import DeepSeekProvider
from briefing.providers.google import GoogleProvider


def test_resolve_provider_deepseek_default(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    provider, api_key = resolve_provider()
    assert isinstance(provider, DeepSeekProvider)
    assert api_key == "sk-test"


def test_resolve_provider_google(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "google")
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "google-key")
    provider, api_key = resolve_provider()
    assert isinstance(provider, GoogleProvider)
    assert api_key == "google-key"


def test_resolve_provider_missing_key_exits(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        resolve_provider()


def test_resolve_provider_unknown_exits(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    with pytest.raises(SystemExit):
        resolve_provider()


def test_apply_provider_defaults_fills_model_and_url():
    provider = GoogleProvider()
    config = parse_query_params("/")
    result = apply_provider_defaults(config, provider)
    assert result["model"] == "gemini-2.5-flash"
    assert "generativelanguage.googleapis.com" in result["api_url"]


def test_apply_provider_defaults_query_override_wins():
    provider = GoogleProvider()
    config = parse_query_params("/?model=custom-model")
    result = apply_provider_defaults(config, provider)
    assert result["model"] == "custom-model"
```

Also update existing tests: remove assertions on `config["provider"]`; remove `model`/`api_url` from default assertions in `test_all_defaults_when_no_query_string` (those come from `apply_provider_defaults` now).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL on new tests; some existing tests fail on removed `provider` key

- [ ] **Step 3: Write minimal implementation**

In `config.py`:
- Remove `"provider"`, `"model"`, `"api_url"` from `DEFAULTS`
- Add imports for `get_provider`, `LLMProvider`
- Add `resolve_provider()`:

```python
def resolve_provider() -> tuple[LLMProvider, str]:
    import sys
    from briefing.providers import get_provider

    name = os.environ.get("LLM_PROVIDER", "deepseek")
    try:
        provider = get_provider(name)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get(provider.api_key_env, "")
    if not api_key:
        print(
            f"ERROR: {provider.api_key_env} environment variable not set "
            f"(required for LLM_PROVIDER={name})",
            file=sys.stderr,
        )
        sys.exit(1)
    return provider, api_key
```

- Add `apply_provider_defaults()`:

```python
def apply_provider_defaults(config: dict[str, str], provider: LLMProvider) -> dict[str, str]:
    result = dict(config)
    if "model" not in result:
        result["model"] = provider.default_model
    if "api_url" not in result:
        result["api_url"] = provider.default_api_url
    return result
```

Update `parse_query_params` to also accept `model` and `api_url` as optional query overrides (add them to a separate `OPTIONAL_OVERRIDES` set or handle outside DEFAULTS loop):

```python
OPTIONAL_LLM_KEYS = ("model", "api_url")

def parse_query_params(path: str) -> dict[str, str]:
    ...
    for key in OPTIONAL_LLM_KEYS:
        if key in params:
            config[key] = params[key][-1]
    return config
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: PASS

---

### Task 4: Curator — delegate to provider

**Files:**
- Modify: `src/briefing/curator.py`
- Test: `tests/test_curator.py`

**Interfaces:**
- Consumes: `LLMProvider` from Task 2
- Produces: `curate(headlines, config, provider, api_key) -> list[dict]`

- [ ] **Step 1: Update failing tests**

Remove `call_deepseek` tests; update `curate` test to pass a provider mock:

```python
# tests/test_curator.py — replace call_deepseek tests with:
from unittest import mock
from briefing.curator import build_prompt, curate


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
```

Keep `test_build_prompt_includes_headlines` unchanged.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_curator.py -v`
Expected: FAIL — wrong signature

- [ ] **Step 3: Update curator.py**

```python
"""LLM prompt building and curation pipeline."""

import textwrap

from briefing.providers.base import LLMProvider


def build_prompt(headlines: list[dict], story_count: int) -> str:
    ...  # unchanged


def curate(
    headlines: list[dict],
    config: dict[str, str],
    provider: LLMProvider,
    api_key: str,
) -> list[dict]:
    story_count = int(config["story_count"])
    prompt = build_prompt(headlines, story_count)
    return provider.call(prompt, config, api_key)
```

Remove `call_deepseek` entirely.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_curator.py -v`
Expected: PASS

---

### Task 5: Wire CLI and server

**Files:**
- Modify: `src/briefing/cli.py`
- Modify: `src/briefing/server.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `resolve_provider()`, `apply_provider_defaults()` from Task 3; updated `curate()` from Task 4

- [ ] **Step 1: Update cli.py**

```python
from briefing.config import parse_query_params, resolve_provider, apply_provider_defaults
from briefing.providers.base import LLMProvider

# In main():
provider, api_key = resolve_provider()

# In _cmd_refresh():
config = apply_provider_defaults(parse_query_params(...), provider)
stories = curate(headlines, config, provider, api_key)

# In _cmd_serve():
server = BriefingServer(provider, api_key, host=host, port=port)
```

Remove the old `DEEPSEEK_API_KEY` check block.

- [ ] **Step 2: Update server.py**

```python
from briefing.config import apply_provider_defaults
from briefing.providers.base import LLMProvider

class BriefingServer:
    def __init__(self, provider: LLMProvider, api_key: str, host="127.0.0.1", port=8080):
        self._provider = provider
        self._api_key = api_key
        ...

    def refresh_now(self):
        config = apply_provider_defaults(_BriefingHandler.latest_config, self._provider)
        ...
        stories = curate(headlines, config, self._provider, self._api_key)
```

- [ ] **Step 3: Update test_server.py**

All `BriefingServer(api_key="test-key", ...)` → `BriefingServer(get_provider("deepseek"), api_key="test-key", ...)`

- [ ] **Step 4: Run full test suite**

Run: `pytest -v`
Expected: All tests PASS

---

### Task 6: Documentation and deployment config

**Files:**
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `Dockerfile`
- Modify: `README.md`

- [ ] **Step 1: Update `.env.example`**

```
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=
GOOGLE_AI_API_KEY=
```

- [ ] **Step 2: Update `docker-compose.yml`**

```yaml
environment:
  - LLM_PROVIDER=${LLM_PROVIDER:-deepseek}
  - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
  - GOOGLE_AI_API_KEY=${GOOGLE_AI_API_KEY}
  - GLANCE_CONFIG=/glance-config/config/home.yml
```

- [ ] **Step 3: Update `Dockerfile`**

```dockerfile
ENV LLM_PROVIDER="deepseek"
ENV DEEPSEEK_API_KEY=""
ENV GOOGLE_AI_API_KEY=""
```

- [ ] **Step 4: Update `README.md`**

- Document `LLM_PROVIDER` env var
- Add Google AI Studio setup section (get key at https://aistudio.google.com/)
- Update configuration table: remove `provider` row; note `model`/`api_url` defaults depend on provider
- Update troubleshooting table with Google-specific errors

- [ ] **Step 5: Final verification**

Run: `pytest -v`
Expected: All tests PASS

---

## Plan Self-Review

**Spec coverage:**
- Provider selection via env var → Task 3, 5
- API key validation → Task 3
- Provider modules → Tasks 1, 2
- Curator delegation → Task 4
- CLI/Server wiring → Task 5
- Docs/deployment → Task 6
- Out of scope items correctly excluded

**Placeholder scan:** No TBD/TODO entries.

**Type consistency:** `LLMProvider`, `resolve_provider()`, `curate()`, `BriefingServer.__init__` signatures consistent across tasks.
