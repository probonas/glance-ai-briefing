"""LLM provider registry."""
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
