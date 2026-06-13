"""CLI entry point for the briefing Glance extension.

Usage:
    briefing serve              Start the HTTP server
    briefing serve --port 9090  Override port
    briefing refresh            Run the pipeline once, print HTML, exit
    briefing --config /path     Use a specific config file
"""

import argparse
import logging
import os
import sys

from briefing.config import load_config
from briefing.feeds import extract_feed_urls, fetch_headlines
from briefing.curator import curate
from briefing.render import render_html
from briefing.server import BriefingServer


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="briefing",
        description="AI-curated news briefing extension for Glance",
    )
    parser.add_argument(
        "--config", "-c",
        help="Path to briefing.yml config file",
        default=None,
    )
    sub = parser.add_subparsers(dest="command", help="Command to run")

    serve_parser = sub.add_parser("serve", help="Start the HTTP server")
    serve_parser.add_argument("--port", type=int, default=None)
    serve_parser.add_argument("--host", default=None)

    refresh_parser = sub.add_parser("refresh", help="Run pipeline once and exit")

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

    config = load_config(cli_path=args.config)
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    if args.command == "refresh":
        _cmd_refresh(config, api_key)
    elif args.command == "serve":
        _cmd_serve(config, api_key, host=args.host, port=args.port)


def _cmd_refresh(config, api_key: str) -> None:
    """Run the pipeline once and print the HTML."""
    print("Discovering RSS feeds...")
    feed_urls = extract_feed_urls(config.glance_config)
    if not feed_urls:
        print("No RSS feeds found in Glance config.")
        sys.exit(0)

    print(f"Found {len(feed_urls)} feed(s). Fetching headlines...")
    headlines, fetched = fetch_headlines(
        feed_urls, limit=config.curation.headlines_per_feed
    )
    print(f"Fetched {len(headlines)} headlines from {fetched}/{len(feed_urls)} feeds.")

    if not headlines:
        print("No headlines to curate.")
        sys.exit(0)

    print("Curating with DeepSeek...")
    stories = curate(
        headlines, config.ai, config.curation.story_count, api_key
    )
    print(render_html(stories))
    print(f"\n--- {len(stories)} stories ---")


def _cmd_serve(
    config, api_key: str, host: str | None = None, port: int | None = None
) -> None:
    """Start the HTTP server."""
    from dataclasses import replace

    if host or port:
        new_server = replace(
            config.server,
            host=host or config.server.host,
            port=port or config.server.port,
        )
        config = replace(config, server=new_server)

    server = BriefingServer(config, api_key)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
