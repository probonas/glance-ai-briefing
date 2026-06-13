"""Configuration from Glance extension query parameters with defaults.

Glance passes the ``parameters`` block from ``glance.yml`` as query-string
parameters on every request.  This module provides a single function that
extracts those parameters and fills in sensible defaults.

The Glance config path (for RSS feed discovery) is *not* a query parameter
— it comes from the ``GLANCE_CONFIG`` environment variable or the hard-coded
default, because the config file is mounted into the container.
"""

import os
from urllib.parse import urlparse, parse_qs

_DEFAULT_GLANCE_CONFIG = os.path.expanduser("~/glance-config/config/home.yml")

# All values are stored as strings so the parsing is uniform.  Consumers
# coerce to the expected type on use (e.g. int, float, bool).
DEFAULTS: dict[str, str] = {
    "provider": "deepseek",
    "model": "deepseek-chat",
    "api_url": "https://api.deepseek.com/v1/chat/completions",
    "temperature": "0.3",
    "timeout_seconds": "30",
    "story_count": "3",
    "headlines_per_feed": "4",
    "refresh_interval": "14400",
    "timezone": "Europe/Athens",
    "silent_hours_start": "00:00",
    "silent_hours_end": "08:00"
}


def get_glance_config_path() -> str:
    """Return the Glance config path from env var or default."""
    return os.environ.get("GLANCE_CONFIG", _DEFAULT_GLANCE_CONFIG)


def parse_query_params(path: str) -> dict[str, str]:
    """Extract config from a URL path's query string, falling back to defaults.

    Args:
        path: Full request path including query string, e.g.
              ``/?story_count=5&model=deepseek-reasoner``.

    Returns:
        Dict with all known keys set (including ``glance_config`` populated
        from the env var / default, not from query params).
    """
    parsed = urlparse(path)
    params = parse_qs(parsed.query, keep_blank_values=True)

    config = dict(DEFAULTS)
    config["glance_config"] = get_glance_config_path()
    for key in DEFAULTS:
        if key in params:
            config[key] = params[key][-1]  # last value wins for duplicates
    return config
