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
