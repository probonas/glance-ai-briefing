"""HTTP server with Glance extension headers and background refresh thread."""

import logging
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from http.server import HTTPServer, BaseHTTPRequestHandler

from briefing.config import parse_query_params, apply_provider_defaults
from briefing.feeds import extract_feed_urls, fetch_headlines
from briefing.curator import curate
from briefing.render import render_html, render_empty_state
from briefing.providers.base import LLMProvider

logger = logging.getLogger("briefing")


class _BriefingHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves the cached briefing HTML with extension headers."""

    # Set by BriefingServer before starting
    cache: str = ""
    server_title: str = "AI Briefing"
    last_refresh: float = 0.0
    # Shared config dict populated by the most recent GET / request.
    # The refresh thread reads it.  Starts as pure defaults.
    latest_config: dict[str, str] = {}
    config_lock: threading.Lock = threading.Lock()
    # Signalled once when the first GET request updates the config,
    # so the refresh thread waits for real parameters before its first cycle.
    config_ready: threading.Event = threading.Event()

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_plain(200, "ok")
            return

        if self.path == "/" or self.path.startswith("/?"):
            # Parse query parameters (Glance's ``parameters`` block)
            # and update the shared config for the refresh thread.
            config = parse_query_params(self.path)
            with self.config_lock:
                _BriefingHandler.latest_config = config
            _BriefingHandler.config_ready.set()
            age = time.time() - self.last_refresh if self.last_refresh else -1
            if age >= 0:
                logger.info("GET / — serving cached response (%.0fs ago)", age)
            else:
                logger.info("GET / — serving empty state (not yet refreshed)")
            self._send_html(200, self.cache)
            return

        self._send_plain(404, "not found")

    def _send_html(self, code: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Widget-Title", self.server_title)
        self.send_header("Widget-Content-Type", "html")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_plain(self, code: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        """Override to use our logger instead of stderr."""
        logger.debug("%s %s", self.address_string(), format % args)


class BriefingServer:
    """Manages the HTTP server and background refresh thread.

    The background thread re-parses Glance config, fetches headlines,
    sends them to the configured LLM provider, and updates the cache on
    every cycle.

    Configuration is read from query parameters (Glance's ``parameters``
    block) on each GET request and applied on the next refresh cycle.
    """

    def __init__(
        self, provider: LLMProvider, api_key: str, host: str = "127.0.0.1", port: int = 8080
    ) -> None:
        self._provider = provider
        self._api_key = api_key
        self._cache = render_empty_state()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._retry_count = 0
        self._refresh_thread: threading.Thread | None = None

        # Seed the handler's shared config with defaults so the refresh
        # thread has something to use before the first request arrives.
        _BriefingHandler.latest_config = parse_query_params("/")
        _BriefingHandler.config_lock = threading.Lock()
        _BriefingHandler.cache = self._cache

        self._httpd = HTTPServer((host, port), _BriefingHandler)

    @property
    def cache(self) -> str:
        with self._lock:
            return self._cache

    def set_cache(self, html: str) -> None:
        with self._lock:
            self._cache = html
        _BriefingHandler.cache = html
        _BriefingHandler.last_refresh = time.time()

    def serve_forever(self) -> None:
        """Start the HTTP server and background refresh thread.

        Blocks until shutdown() is called.
        """
        self._start_refresh_thread()
        logger.info(
            "Briefing server starting on %s:%d",
            self._httpd.server_name,
            self._httpd.server_port,
        )
        try:
            self._httpd.serve_forever()
        except KeyboardInterrupt:
            pass

    def shutdown(self) -> None:
        """Stop the server and background thread."""
        self._stop_event.set()
        self._httpd.shutdown()

    def refresh_now(self) -> bool:
        """Run one pipeline attempt.  Called by the background thread.

        Returns:
            True on success (new stories cached), False otherwise.
        """
        config = apply_provider_defaults(_BriefingHandler.latest_config, self._provider)
        try:
            logger.info("Refresh cycle starting")
            feed_urls = extract_feed_urls(config["glance_config"])
            if not feed_urls:
                logger.warning("No RSS feeds found in Glance config")
                if "<p" not in self.cache:
                    self.set_cache(render_empty_state())
                return False

            headlines, fetched = fetch_headlines(
                feed_urls, limit=int(config["headlines_per_feed"])
            )
            logger.info("Fetched %d headlines from %d/%d feeds",
                        len(headlines), fetched, len(feed_urls))

            if not headlines:
                logger.warning("No headlines fetched — keeping previous cache")
                return False

            stories = curate(headlines, config, self._provider, self._api_key)
            if stories:
                html = render_html(stories, config)
                self.set_cache(html)
                logger.info("Refresh complete — %d stories cached", len(stories))
                return True
            else:
                logger.warning("No stories returned from AI — keeping previous cache")
                return False
        except Exception:
            logger.exception("Refresh cycle failed")
            return False

    @classmethod
    def is_silent_hours(cls, now: datetime | None = None) -> bool:
        """Check whether *now* falls within the configured silent hours.

        Args:
            now: Optional datetime to check.  Defaults to the current time
                in the configured timezone.

        Returns:
            True if *now* is within the silent-hours window (inclusive on
            both ends), False otherwise.
        """
        config = _BriefingHandler.latest_config
        if now is None:
            now = datetime.now(ZoneInfo(config["timezone"]))
        start = datetime.strptime(config["silent_hours_start"], "%H:%M").time()
        end = datetime.strptime(config["silent_hours_end"], "%H:%M").time()
        return start <= now.time() <= end

    def _start_refresh_thread(self) -> None:
        """Start the background refresh loop in a daemon thread."""
        def _loop() -> None:
            # Wait for the first GET request to deliver real config
            # before running the first refresh cycle.
            logger.info("Waiting for Glance config parameters...")
            _BriefingHandler.config_ready.wait()
            success = self.refresh_now()
            self._retry_count = 0 if success else 1

            while not self._stop_event.is_set():
                interval = int(_BriefingHandler.latest_config["refresh_interval"])
                if self._retry_count > 0:
                    wait = min(interval, 2 * (2 ** (self._retry_count - 1)))
                else:
                    wait = interval
                if self._stop_event.wait(wait):
                    break
                if not self.is_silent_hours():
                    success = self.refresh_now()
                    self._retry_count = 0 if success else self._retry_count + 1
                else:
                    logger.info("Silent hours. Skipped refreshing...")

        self._refresh_thread = threading.Thread(target=_loop, daemon=True)
        self._refresh_thread.start()
