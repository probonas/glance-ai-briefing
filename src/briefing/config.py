"""Configuration loading with defaults and YAML file support."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_DEFAULT_GLANCE_CONFIG = os.path.expanduser("~/glance-config/config/home.yml")


@dataclass(frozen=True)
class AIConfig:
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    api_url: str = "https://api.deepseek.com/v1/chat/completions"
    temperature: float = 0.3
    timeout_seconds: int = 30


@dataclass(frozen=True)
class CurationConfig:
    story_count: int = 3
    headlines_per_feed: int = 4


@dataclass(frozen=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8080


@dataclass(frozen=True)
class Config:
    glance_config: str = field(
        default_factory=lambda: os.environ.get(
            "GLANCE_CONFIG",
            _DEFAULT_GLANCE_CONFIG,
        )
    )
    ai: AIConfig = field(default_factory=AIConfig)
    curation: CurationConfig = field(default_factory=CurationConfig)
    refresh_interval: int = 14400
    server: ServerConfig = field(default_factory=ServerConfig)


def _discover_config_path(cli_path: str | None = None) -> str | None:
    """Find the first existing config file from:
    1. CLI flag (--config)
    2. ./briefing.yml
    3. ~/.config/briefing/briefing.yml
    Returns None if no file found.
    """
    if cli_path and Path(cli_path).exists():
        return cli_path
    if Path("briefing.yml").exists():
        return "briefing.yml"
    home_config = Path.home() / ".config" / "briefing" / "briefing.yml"
    if home_config.exists():
        return str(home_config)
    return None


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Lists are replaced, not merged."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(cli_path: str | None = None) -> Config:
    """Load configuration from YAML file and apply defaults.

    Args:
        cli_path: Optional path from --config CLI flag.

    Returns:
        Config with all values set (defaults + file overrides).
    """
    defaults = {
        "glance_config": os.environ.get("GLANCE_CONFIG", _DEFAULT_GLANCE_CONFIG),
        "ai": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_url": "https://api.deepseek.com/v1/chat/completions",
            "temperature": 0.3,
            "timeout_seconds": 30,
        },
        "curation": {
            "story_count": 3,
            "headlines_per_feed": 4,
        },
        "refresh_interval": 14400,
        "server": {
            "host": "127.0.0.1",
            "port": 8080,
        },
    }

    config_path = _discover_config_path(cli_path)
    if config_path:
        with open(config_path) as f:
            user = yaml.safe_load(f) or {}
        merged = _deep_merge(defaults, user)
    else:
        merged = defaults

    return Config(
        glance_config=merged["glance_config"],
        ai=AIConfig(**merged["ai"]),
        curation=CurationConfig(**merged["curation"]),
        refresh_interval=merged["refresh_interval"],
        server=ServerConfig(**merged["server"]),
    )
