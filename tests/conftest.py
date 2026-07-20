import os
import pytest


@pytest.fixture(autouse=True)
def _clear_env_vars():
    """Remove env vars that may come from .env so tests are isolated."""
    for key in ("LLM_API_KEY", "LLM_PROVIDER", "GLANCE_CONFIG"):
        os.environ.pop(key, None)
