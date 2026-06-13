"""CLI entry point for the briefing Glance extension.

Usage:
    briefing serve              Start the HTTP server
    briefing serve --port 9090  Override port
    briefing refresh            Run the pipeline once, print HTML, exit

Configuration is passed by Glance through the extension ``parameters``
block in ``glance.yml`` — no separate config file needed.  Example::

    - type: extension
      url: http://localhost:8080
      parameters:
        story_count: 5
        model: deepseek-reasoner
        refresh_interval: 7200
"""

import argparse
import logging
import os
import sys

from briefing.config import parse_query_params
from briefing.feeds import extract_feed_urls, fetch_headlines
from briefing.curator import curate
from briefing.render import render_html
from briefing.server import BriefingServer


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="briefing",
        description="AI-curated news briefing extension for Glance",
    )
    sub = parser.add_subparsers(dest="command", help="Command to run")

    serve_parser = sub.add_parser("serve", help="Start the HTTP server")
    serve_parser.add_argument("--port", type=int, default=8080)
    serve_parser.add_argument("--host", default="127.0.0.1")

    refresh_parser = sub.add_parser("refresh", help="Run pipeline once and exit")
    refresh_parser.add_argument(
        "--params", default="",
        help="Query-string-style config params, e.g. 'story_count=5&model=deepseek-reasoner'",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    if args.command == "refresh":
        _cmd_refresh(api_key, args.params)
    elif args.command == "serve":
        _cmd_serve(api_key, host=args.host, port=args.port)


def _cmd_refresh(api_key: str, params: str) -> None:
    """Run the pipeline once and print the HTML."""
    config = parse_query_params(f"/?{params}" if params else "/")

    print("Discovering RSS feeds...")
    feed_urls = extract_feed_urls(config["glance_config"])
    if not feed_urls:
        print("No RSS feeds found in Glance config.")
        sys.exit(0)

    print(f"Found {len(feed_urls)} feed(s). Fetching headlines...")
    headlines, fetched = fetch_headlines(
        feed_urls, limit=int(config["headlines_per_feed"])
    )
    print(f"Fetched {len(headlines)} headlines from {fetched}/{len(feed_urls)} feeds.")

    if not headlines:
        print("No headlines to curate.")
        sys.exit(0)

    print("Curating with AI...")
    stories = curate(headlines, config, api_key)
    print(render_html(stories))
    print(f"\n--- {len(stories)} stories ---")


def _cmd_serve(api_key: str, host: str, port: int) -> None:
    """Start the HTTP server."""
    server = BriefingServer(api_key, host=host, port=port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
