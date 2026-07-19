"""LLM prompt building and curation pipeline."""

import textwrap

from briefing.providers.base import LLMProvider


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


def curate(
    headlines: list[dict],
    config: dict[str, str],
    provider: LLMProvider,
    api_key: str,
) -> list[dict]:
    """Full curation pipeline: build prompt, call provider, return stories.

    Args:
        headlines: List of headline dicts from :func:`~briefing.feeds.fetch_headlines`.
        config: Config dict from :func:`~briefing.config.parse_query_params`.
        provider: LLM provider instance implementing :class:`~briefing.providers.base.LLMProvider`.
        api_key: API key for the provider.
    """
    story_count = int(config["story_count"])
    prompt = build_prompt(headlines, story_count)
    return provider.call(prompt, config, api_key)
