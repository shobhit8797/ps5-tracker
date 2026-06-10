"""Command-line interface for the tracker."""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Sequence
from datetime import datetime

from ps5tracker.config import load_settings
from ps5tracker.models import Stock
from ps5tracker.notifier import format_report, send_telegram
from ps5tracker.runner import execute, run_once


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PS5 availability tracker")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run checks and print the report, but don't notify",
    )
    parser.add_argument(
        "--test-telegram",
        action="store_true",
        help="send a test Telegram message and exit",
    )
    parser.add_argument(
        "--platform",
        action="append",
        default=None,
        help="restrict to these platform(s); repeatable",
    )
    parser.add_argument("--config", default=None, help="path to config.yaml")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    settings = load_settings(args.config) if args.config else load_settings()

    if args.test_telegram:
        send_telegram(
            settings.telegram_token,
            settings.telegram_chat_id,
            "✅ PS5 tracker: Telegram is wired up correctly.",
        )
        print("Test message sent.")
        return 0

    if args.platform:
        for name in list(settings.platforms):
            settings.platforms[name]["enabled"] = name in args.platform

    if args.dry_run:
        results = asyncio.run(run_once(settings))
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        print(format_report(results, ts))
        in_stock = sum(1 for r in results if r.status == Stock.IN_STOCK)
        print(
            f"\n[dry-run] {len(results)} results, {in_stock} in stock. "
            f"No notification sent."
        )
        return 0

    execute(settings)
    return 0
