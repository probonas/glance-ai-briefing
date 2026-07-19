from dataclasses import dataclass
from briefing.providers.base import _call_openai_compatible


@dataclass(frozen=True)
class DeepSeekProvider:
    name: str = "deepseek"
    default_model: str = "deepseek-chat"
    default_api_url: str = "https://api.deepseek.com/v1/chat/completions"

    def call(self, prompt: str, config: dict[str, str], api_key: str) -> list[dict]:
        return _call_openai_compatible(prompt, config, api_key)
