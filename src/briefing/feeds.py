"""RSS feed discovery from Glance config and headline fetching."""

from pathlib import Path

import feedparser
import yaml


def extract_feed_urls(config_path: str) -> list[str]:
    """Parse a Glance home.yml and return all unique RSS feed URLs."""
    config = Path(config_path)
    if not config.exists():
        return []

    with config.open() as f:
        pages = yaml.safe_load(f)

    urls: list[str] = []
    if not isinstance(pages, list):
        pages = [pages]

    for page in pages:
        for column in page.get("columns", []):
            for widget in column.get("widgets", []):
                _collect_rss_urls(widget, urls)

    return list(dict.fromkeys(urls))


def _collect_rss_urls(widget: dict, urls: list[str]) -> None:
    """Recursively walk a widget tree collecting RSS feed URLs."""
    if widget.get("type") == "rss":
        for feed in widget.get("feeds", []):
            url = feed.get("url")
            if url:
                urls.append(url)
    for sub in widget.get("widgets", []):
        _collect_rss_urls(sub, urls)


def fetch_headlines(
    feed_urls: list[str], limit: int = 4
) -> tuple[list[dict], int]:
    """Fetch up to `limit` headlines from each RSS feed.

    Returns:
        (headlines, fetched_count) where headlines is a list of dicts
        with keys 'title', 'url', 'source', and fetched_count is the
        number of feeds successfully fetched.
    """
    headlines: list[dict] = []
    fetched = 0

    for url in feed_urls:
        try:
            parsed = feedparser.parse(url)
            entries = parsed.entries[:limit]
            if not entries:
                continue
            fetched += 1
            source = parsed.feed.get("title", url)
            for entry in entries:
                headlines.append({
                    "title": entry.get("title", "").strip(),
                    "url": entry.get("link", ""),
                    "source": source,
                })
        except Exception:
            pass

    return headlines, fetched
