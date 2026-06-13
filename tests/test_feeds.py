# tests/test_feeds.py
import os
import tempfile
import yaml
from briefing.feeds import extract_feed_urls, fetch_headlines


def _write_glance_config(content: dict, dir_path: str) -> str:
    """Write a glance home.yml and return its path."""
    path = os.path.join(dir_path, "home.yml")
    with open(path, "w") as f:
        yaml.dump(content, f)
    return path


def test_extract_rss_feeds_from_single_column():
    """Finds RSS feeds in a simple single-column page."""
    with tempfile.TemporaryDirectory() as d:
        config_path = _write_glance_config({
            "columns": [{
                "widgets": [
                    {"type": "rss", "feeds": [
                        {"url": "https://example.com/feed.xml"},
                        {"url": "https://other.com/rss"},
                    ]},
                ],
            }],
        }, d)

        urls = extract_feed_urls(config_path)
        assert urls == ["https://example.com/feed.xml", "https://other.com/rss"]


def test_extract_rss_feeds_from_nested_widgets():
    """Finds RSS feeds nested inside group widgets."""
    with tempfile.TemporaryDirectory() as d:
        config_path = _write_glance_config({
            "columns": [{
                "widgets": [
                    {"type": "group", "widgets": [
                        {"type": "rss", "feeds": [
                            {"url": "https://nested.example.com/feed.xml"},
                        ]},
                    ]},
                ],
            }],
        }, d)

        urls = extract_feed_urls(config_path)
        assert urls == ["https://nested.example.com/feed.xml"]


def test_extract_rss_feeds_across_columns():
    """Collects RSS feeds from all columns."""
    with tempfile.TemporaryDirectory() as d:
        config_path = _write_glance_config([
            {"columns": [{"widgets": [
                {"type": "rss", "feeds": [{"url": "https://col1.com/feed.xml"}]},
            ]}]},
            {"columns": [{"widgets": [
                {"type": "rss", "feeds": [{"url": "https://col2.com/rss"}]},
            ]}]},
        ], d)

        urls = extract_feed_urls(config_path)
        assert len(urls) == 2
        assert "https://col1.com/feed.xml" in urls
        assert "https://col2.com/rss" in urls


def test_extract_no_rss_feeds_returns_empty():
    """Returns empty list when no RSS widgets exist."""
    with tempfile.TemporaryDirectory() as d:
        config_path = _write_glance_config({
            "columns": [{"widgets": [
                {"type": "weather"},
                {"type": "bookmarks"},
            ]}],
        }, d)

        urls = extract_feed_urls(config_path)
        assert urls == []


def test_extract_deduplicates_urls():
    """Duplicate feed URLs are removed."""
    with tempfile.TemporaryDirectory() as d:
        config_path = _write_glance_config({
            "columns": [{"widgets": [
                {"type": "rss", "feeds": [
                    {"url": "https://example.com/feed.xml"},
                ]},
                {"type": "rss", "feeds": [
                    {"url": "https://example.com/feed.xml"},
                ]},
            ]}],
        }, d)

        urls = extract_feed_urls(config_path)
        assert urls == ["https://example.com/feed.xml"]
