# Google AI Studio Provider Support — Design Spec

**Date:** 2026-07-19  
**Status:** Approved

## Summary

Expand glance-ai-briefing to support Google AI Studio (Gemini) as an alternative LLM provider alongside DeepSeek. Provider selection is via the `LLM_PROVIDER` environment variable. Only the active provider's API key is required at startup.

## Requirements

### Provider selection

- `LLM_PROVIDER` env var selects the provider (default: `deepseek`)
- Valid values: `deepseek`, `google`
- Unknown provider → exit with clear error at startup
- Glance `parameters.provider` query param is **removed** from config defaults (env var is sole source of truth)

### API keys

| Provider | Env var | Required when |
|---|---|---|
| DeepSeek | `DEEPSEEK_API_KEY` | `LLM_PROVIDER=deepseek` (default) |
| Google | `GOOGLE_AI_API_KEY` | `LLM_PROVIDER=google` |

Missing key for the active provider → exit with error naming the correct env var.

### Provider defaults

| Provider | Default model | Default api_url |
|---|---|---|
| `deepseek` | `deepseek-chat` | `https://api.deepseek.com/v1/chat/completions` |
| `google` | `gemini-2.5-flash` | `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` |

Glance `parameters` can still override `model`, `api_url`, `temperature`, `timeout_seconds`, etc.

### Architecture

Full provider abstraction with separate modules:

```
src/briefing/providers/
├── __init__.py       # get_provider(name) factory
├── base.py           # LLMProvider Protocol + shared HTTP helper
├── deepseek.py       # DeepSeekProvider
└── google.py         # GoogleProvider
```

Both providers use Google's and DeepSeek's OpenAI-compatible chat completions API. Shared HTTP/parsing logic lives in `base.py` as `_call_openai_compatible()`.

### LLMProvider interface

```python
class LLMProvider(Protocol):
    name: str
    api_key_env: str
    default_model: str
    default_api_url: str

    def call(self, prompt: str, config: dict[str, str], api_key: str) -> list[dict]:
        ...
```

### Config changes

- `resolve_provider() -> tuple[LLMProvider, str]` — reads env, validates, returns provider + key
- `apply_provider_defaults(config, provider)` — merges provider defaults; Glance overrides win
- Remove `provider` from `DEFAULTS` dict

### Curator changes

- Remove `call_deepseek()` — provider handles API call
- `curate(headlines, config, provider, api_key)` — builds prompt, delegates to `provider.call()`

### CLI / Server changes

- `cli.py`: call `resolve_provider()` at startup; pass provider to server and refresh
- `server.py`: store provider instance; pass to `curate()`

### Documentation & deployment

- `.env.example`: add `LLM_PROVIDER`, `GOOGLE_AI_API_KEY`
- `docker-compose.yml`: pass through new env vars
- `Dockerfile`: document new env vars
- `README.md`: document both providers, Google AI Studio setup

### Testing

- `tests/test_providers.py` — factory lookup, HTTP call with mocks, markdown fence stripping
- `tests/test_config.py` — `resolve_provider()`, missing key, unknown provider
- `tests/test_curator.py` — updated signatures, provider delegation

### Out of scope

- Runtime provider switching via Glance parameters
- Google native SDK (OpenAI-compatible endpoint is sufficient)
- Model listing / validation against provider APIs

## Error handling

- Startup: fail fast with named env var if key missing or provider unknown
- Runtime API errors: unchanged — logged in refresh cycle, previous cache retained

## Migration

Existing deployments using DeepSeek require no changes (`LLM_PROVIDER` defaults to `deepseek`, `DEEPSEEK_API_KEY` still used).

To switch to Google:

```bash
export LLM_PROVIDER=google
export GOOGLE_AI_API_KEY=your-key-from-aistudio.google.com
```
