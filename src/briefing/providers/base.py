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
