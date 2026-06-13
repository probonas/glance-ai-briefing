# tests/test_config.py
import os
from briefing.config import parse_query_params, get_glance_config_path, DEFAULTS


def test_all_defaults_when_no_query_string():
    """Without any query parameters, all defaults are applied."""
    config = parse_query_params("/")
    assert config["provider"] == "deepseek"
    assert config["model"] == "deepseek-chat"
    assert config["api_url"] == "https://api.deepseek.com/v1/chat/completions"
    assert config["temperature"] == "0.3"
    assert config["timeout_seconds"] == "30"
    assert config["story_count"] == "3"
    assert config["headlines_per_feed"] == "4"
    assert config["refresh_interval"] == "14400"
    assert config["timezone"] == "Europe/Athens"
    assert config["silent_hours_start"] == "00:00"
    assert config["silent_hours_end"] == "08:00"
    assert config["glance_config"] == os.path.expanduser(
        "~/glance-config/config/home.yml"
    )


def test_query_params_override_defaults():
    """Query parameters override the defaults they specify."""
    config = parse_query_params(
        "/?story_count=5&model=deepseek-reasoner&temperature=0.7"
    )
    assert config["story_count"] == "5"
    assert config["model"] == "deepseek-reasoner"
    assert config["temperature"] == "0.7"
    assert config["provider"] == "deepseek"
    assert config["timeout_seconds"] == "30"


def test_silent_hours_override_via_query():
    """Silent hours defaults can be overridden via query parameters."""
    config = parse_query_params(
        "/?silent_hours_start=22:00&silent_hours_end=06:00&timezone=America/New_York"
    )
    assert config["silent_hours_start"] == "22:00"
    assert config["silent_hours_end"] == "06:00"
    assert config["timezone"] == "America/New_York"
    assert config["story_count"] == "3"  # other defaults still apply


def test_partial_params_still_get_defaults():
    """A query string with only some params still applies defaults for others."""
    config = parse_query_params("/?headlines_per_feed=10")
    assert config["headlines_per_feed"] == "10"
    assert config["model"] == "deepseek-chat"
    assert config["story_count"] == "3"


def test_glance_config_from_env_var():
    """GLANCE_CONFIG env var overrides the default path."""
    os.environ["GLANCE_CONFIG"] = "/custom/glance/home.yml"
    try:
        assert get_glance_config_path() == "/custom/glance/home.yml"
    finally:
        del os.environ["GLANCE_CONFIG"]


def test_glance_config_not_overridable_by_query_param():
    """glance_config is NOT a query parameter — env/default only."""
    config = parse_query_params("/?glance_config=/evil/path")
    assert config["glance_config"] == os.path.expanduser(
        "~/glance-config/config/home.yml"
    )


def test_last_duplicate_param_wins():
    """When a parameter appears multiple times, the last value wins."""
    config = parse_query_params("/?story_count=3&story_count=7")
    assert config["story_count"] == "7"


def test_path_without_query_is_ignored():
    """The path portion is irrelevant; only the query string matters."""
    config = parse_query_params("/some/other/path?story_count=4")
    assert config["story_count"] == "4"


def test_health_endpoint_style_path():
    """A path without query string just returns defaults."""
    config = parse_query_params("/health")
    assert config["provider"] == "deepseek"
