"""HTTP server with Glance extension headers and background refresh thread."""

import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

from briefing.config import Config
from briefing.feeds import extract_feed_urls, fetch_headlines
from briefing.curator import curate
from briefing.render import render_html, render_empty_state

logger = logging.getLogger("briefing")


class _BriefingHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves the cached briefing HTML with extension headers."""

    # Set by BriefingServer before starting
    cache: str = ""
    server_title: str = "AI Briefing"

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_plain(200, "ok")
            return

        if self.path == "/":
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
    sends them to DeepSeek, and updates the cache on every cycle.
    """

    def __init__(
        self, config: Config, api_key: str, port: int | None = None
    ) -> None:
        self.config = config
        self.api_key = api_key
        self._cache = render_empty_state()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._refresh_thread: threading.Thread | None = None

        # Ensure the handler class reflects the initial cache
        _BriefingHandler.cache = self._cache

        host = config.server.host
        port = port if port is not None else config.server.port
        self._httpd = HTTPServer((host, port), _BriefingHandler)

    @property
    def cache(self) -> str:
        with self._lock:
            return self._cache

    def set_cache(self, html: str) -> None:
        with self._lock:
            self._cache = html
        _BriefingHandler.cache = html

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

    def refresh_now(self) -> None:
        """Run the full pipeline immediately. Called by the background thread."""
        try:
            logger.info("Refresh cycle starting")
            feed_urls = extract_feed_urls(self.config.glance_config)
            if not feed_urls:
                logger.warning("No RSS feeds found in Glance config")
                if "<p" not in self.cache:
                    self.set_cache(render_empty_state())
                return

            headlines, fetched = fetch_headlines(
                feed_urls, limit=self.config.curation.headlines_per_feed
            )
            logger.info("Fetched %d headlines from %d/%d feeds",
                        len(headlines), fetched, len(feed_urls))

            if not headlines:
                logger.warning("No headlines fetched — keeping previous cache")
                return

            stories = curate(
                headlines,
                self.config.ai,
                self.config.curation.story_count,
                self.api_key,
            )
            if stories:
                html = render_html(stories)
                self.set_cache(html)
                logger.info("Refresh complete — %d stories cached", len(stories))
            else:
                logger.warning("No stories returned from AI — keeping previous cache")
        except Exception:
            logger.exception("Refresh cycle failed")

    def _start_refresh_thread(self) -> None:
        """Start the background refresh loop in a daemon thread."""
        def _loop() -> None:
            # Run first refresh immediately
            self.refresh_now()
            while not self._stop_event.wait(self.config.refresh_interval):
                self.refresh_now()

        self._refresh_thread = threading.Thread(target=_loop, daemon=True)
        self._refresh_thread.start()
