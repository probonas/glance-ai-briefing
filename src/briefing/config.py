"""Configuration from Glance extension query parameters with defaults.

Glance passes the ``parameters`` block from ``glance.yml`` as query-string
parameters on every request.  This module provides a single function that
extracts those parameters and fills in sensible defaults.

The Glance config path (for RSS feed discovery) is *not* a query parameter
— it comes from the ``GLANCE_CONFIG`` environment variable or the hard-coded
default, because the config file is mounted into the container.
"""

import sys
import os
from urllib.parse import urlparse, parse_qs

from briefing.providers import get_provider
from briefing.providers.base import LLMProvider

_DEFAULT_GLANCE_CONFIG = os.path.expanduser("~/glance-config/config/home.yml")

# All values are stored as strings so the parsing is uniform.  Consumers
# coerce to the expected type on use (e.g. int, float, bool).
DEFAULTS: dict[str, str] = {
    "temperature": "0.3",
    "timeout_seconds": "30",
    "story_count": "3",
    "headlines_per_feed": "4",
    "refresh_interval": "14400",
    "timezone": "Europe/Athens",
    "silent_hours_start": "00:00",
    "silent_hours_end": "08:00"
}

# LLM keys that can be overridden via query params but have no static default
# — their defaults come from the provider at runtime.
OPTIONAL_LLM_KEYS = ("model", "api_url")


def get_glance_config_path() -> str:
    """Return the Glance config path from env var or default."""
    return os.environ.get("GLANCE_CONFIG", _DEFAULT_GLANCE_CONFIG)


def resolve_provider() -> tuple[LLMProvider, str]:
    """Read ``LLM_PROVIDER`` env var, look up the provider, validate the API key.

    Returns:
        ``(provider, api_key)`` tuple.

    Raises:
        SystemExit: If the provider name is unknown or the required API key
        environment variable is not set.
    """
    name = os.environ.get("LLM_PROVIDER", "deepseek")
    try:
        provider = get_provider(name)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("LLM_API_KEY", "")
    if not api_key:
        print(
            f"ERROR: LLM_API_KEY environment variable not set "
            f"(required for LLM_PROVIDER={name})",
            file=sys.stderr,
        )
        sys.exit(1)
    return provider, api_key


def apply_provider_defaults(
    config: dict[str, str], provider: LLMProvider
) -> dict[str, str]:
    """Merge provider-specific defaults into *config* (query-param overrides win)."""
    result = dict(config)
    if "model" not in result:
        result["model"] = provider.default_model
    if "api_url" not in result:
        result["api_url"] = provider.default_api_url
    return result


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
    for key in OPTIONAL_LLM_KEYS:
        if key in params:
            config[key] = params[key][-1]
    return config
