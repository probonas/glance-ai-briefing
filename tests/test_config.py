# tests/test_config.py
import os
import tempfile
from pathlib import Path
from briefing.config import Config, AIConfig, CurationConfig, ServerConfig, load_config


def test_default_config():
    """Without any config file, all defaults are applied."""
    config = load_config()
    assert config.ai.provider == "deepseek"
    assert config.ai.model == "deepseek-chat"
    assert config.ai.api_url == "https://api.deepseek.com/v1/chat/completions"
    assert config.ai.temperature == 0.3
    assert config.ai.timeout_seconds == 30
    assert config.curation.story_count == 3
    assert config.curation.headlines_per_feed == 4
    assert config.refresh_interval == 14400
    assert config.server.host == "127.0.0.1"
    assert config.server.port == 8080
    assert config.glance_config == os.path.expanduser("~/glance-config/config/home.yml")


def test_load_from_yaml_file():
    """A briefing.yml file overrides the defaults it specifies."""
    yaml_content = """
ai:
  model: deepseek-reasoner
  temperature: 0.7
curation:
  story_count: 5
server:
  port: 9090
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        config = load_config(cli_path=tmp_path)
        # Overridden values
        assert config.ai.model == "deepseek-reasoner"
        assert config.ai.temperature == 0.7
        assert config.curation.story_count == 5
        assert config.server.port == 9090
        # Defaults remain for unspecified keys
        assert config.ai.provider == "deepseek"
        assert config.ai.timeout_seconds == 30
        assert config.refresh_interval == 14400
        assert config.server.host == "127.0.0.1"
    finally:
        os.unlink(tmp_path)


def test_partial_yaml_does_not_crash():
    """A YAML file with only one section still applies defaults for others."""
    yaml_content = """
server:
  port: 3000
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        config = load_config(cli_path=tmp_path)
        assert config.server.port == 3000
        assert config.ai.model == "deepseek-chat"
        assert config.curation.story_count == 3
    finally:
        os.unlink(tmp_path)


def test_glance_config_env_override():
    """GLANCE_CONFIG env var overrides the default path."""
    os.environ["GLANCE_CONFIG"] = "/custom/glance/home.yml"
    config = load_config()
    assert config.glance_config == "/custom/glance/home.yml"
    del os.environ["GLANCE_CONFIG"]
