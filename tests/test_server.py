# tests/test_server.py
import json
import threading
import time
import urllib.request
from briefing.server import BriefingServer
from briefing.providers import get_provider


def _get_free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def test_server_returns_extension_headers():
    """GET / returns Widget-Title and Widget-Content-Type headers."""
    port = _get_free_port()
    server = BriefingServer(get_provider("deepseek"), api_key="test-key", port=port)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/")
        response = urllib.request.urlopen(req, timeout=5)
        assert response.status == 200
        assert response.getheader("Widget-Title") == "AI Briefing"
        assert response.getheader("Widget-Content-Type") == "html"
        body = response.read().decode("utf-8")
        assert len(body) > 0
    finally:
        server.shutdown()


def test_health_endpoint():
    """GET /health returns 200 and 'ok'."""
    port = _get_free_port()
    server = BriefingServer(get_provider("deepseek"), api_key="test-key", port=port)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
        response = urllib.request.urlopen(req, timeout=5)
        assert response.status == 200
        body = response.read().decode("utf-8").strip()
        assert body == "ok"
    finally:
        server.shutdown()


def test_initial_cache_is_empty_state():
    """Before any refresh, the server returns the empty state."""
    port = _get_free_port()
    server = BriefingServer(get_provider("deepseek"), api_key="test-key", port=port)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/")
        response = urllib.request.urlopen(req, timeout=5)
        body = response.read().decode("utf-8")
        assert "No briefing available" in body
    finally:
        server.shutdown()


def test_server_can_set_cache():
    """The server's cache can be updated and subsequent requests see it."""
    port = _get_free_port()
    server = BriefingServer(get_provider("deepseek"), api_key="test-key", port=port)

    server.set_cache("<p>Hello World</p>")

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/")
        response = urllib.request.urlopen(req, timeout=5)
        body = response.read().decode("utf-8")
        assert "Hello World" in body
    finally:
        server.shutdown()


def test_query_params_update_config():
    """Query parameters on GET / update the shared config."""
    port = _get_free_port()
    server = BriefingServer(get_provider("deepseek"), api_key="test-key", port=port)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)

    try:
        # Send a request with query params
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/?story_count=7&model=custom-model"
        )
        response = urllib.request.urlopen(req, timeout=5)
        assert response.status == 200

        # The handler should have parsed and stored the config
        from briefing.server import _BriefingHandler
        with _BriefingHandler.config_lock:
            config = _BriefingHandler.latest_config
        assert config["story_count"] == "7"
        assert config["model"] == "custom-model"
        # Unspecified params get defaults
        assert config["refresh_interval"] == "14400"
    finally:
        server.shutdown()

SILENT_CONFIG = {
    "timezone": "UTC",
    "silent_hours_start": "00:00",
    "silent_hours_end": "08:00",
}

def test_is_silent_hours_inside():
    """Returns True when current time is inside silent hours."""
    from briefing.server import BriefingServer, _BriefingHandler
    from datetime import datetime, timezone

    _BriefingHandler.latest_config = SILENT_CONFIG
    now = datetime(2026, 6, 13, 3, 0, 0, tzinfo=timezone.utc)
    assert BriefingServer.is_silent_hours(now=now) is True


def test_is_silent_hours_outside():
    """Returns False when current time is outside silent hours."""
    from briefing.server import BriefingServer, _BriefingHandler
    from datetime import datetime, timezone

    _BriefingHandler.latest_config = SILENT_CONFIG
    now = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)
    assert BriefingServer.is_silent_hours(now=now) is False


def test_is_silent_hours_at_start_boundary():
    """Returns True when current time equals silent_hours_start (inclusive)."""
    from briefing.server import BriefingServer, _BriefingHandler
    from datetime import datetime, timezone

    _BriefingHandler.latest_config = SILENT_CONFIG
    now = datetime(2026, 6, 13, 0, 0, 0, tzinfo=timezone.utc)
    assert BriefingServer.is_silent_hours(now=now) is True


def test_is_silent_hours_at_end_boundary():
    """Returns True when current time equals silent_hours_end (inclusive)."""
    from briefing.server import BriefingServer, _BriefingHandler
    from datetime import datetime, timezone

    _BriefingHandler.latest_config = SILENT_CONFIG
    now = datetime(2026, 6, 13, 8, 0, 0, tzinfo=timezone.utc)
    assert BriefingServer.is_silent_hours(now=now) is True
