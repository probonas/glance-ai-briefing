from dataclasses import dataclass
from briefing.providers.base import _call_openai_compatible


@dataclass(frozen=True)
class GoogleProvider:
    name: str = "google"
    default_model: str = "gemini-3.5-flash"
    default_api_url: str = (
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    )

    def call(self, prompt: str, config: dict[str, str], api_key: str) -> list[dict]:
        return _call_openai_compatible(prompt, config, api_key)
