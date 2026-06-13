"""DeepSeek prompt building, API call, and response parsing."""

import json
import textwrap

import requests

from briefing.config import AIConfig


def build_prompt(headlines: list[dict], story_count: int) -> str:
    """Build the curation prompt from fetched headlines."""
    items = "\n".join(
        f"- [{h['source']}] {h['title']} ({h['url']})"
        for h in headlines
    )
    return textwrap.dedent(f"""
        You are a news editor. Below are recent headlines from multiple news sources.

        Select the {story_count} most globally significant stories right now.
        For each story return a JSON object with these exact keys:
        - "headline": the story title (keep it concise)
        - "source": the news source name
        - "url": the article URL
        - "summary": one sentence, max 15 words, explaining why this matters

        Return ONLY a valid JSON array with {story_count} objects. No markdown, no explanation.

        Headlines:
        {items}
    """).strip()


def call_deepseek(prompt: str, ai_config: AIConfig, api_key: str) -> list[dict]:
    """Send the prompt to DeepSeek and parse the JSON response.

    Raises:
        requests.exceptions.RequestException: on HTTP errors or timeouts.
        json.JSONDecodeError: if the response body is not valid JSON.
        ValueError: if the parsed result is not a list.
    """
    response = requests.post(
        ai_config.api_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": ai_config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": ai_config.temperature,
        },
        timeout=ai_config.timeout_seconds,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"].strip()

    # Some models wrap the JSON in markdown code fences
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    parsed = json.loads(content.strip())
    if not isinstance(parsed, list):
        raise ValueError(f"DeepSeek returned {type(parsed)}, expected list")
    return parsed


def curate(
    headlines: list[dict], ai_config: AIConfig, story_count: int, api_key: str
) -> list[dict]:
    """Full curation pipeline: build prompt, call API, return stories."""
    prompt = build_prompt(headlines, story_count)
    return call_deepseek(prompt, ai_config, api_key)
