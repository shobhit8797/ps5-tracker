"""Orchestrates a single tracking run: check every (platform × product ×
location), apply the notify policy, and send to Telegram."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta

from .config import Settings
from .models import Result, Stock
from .notifier import format_report, send_telegram
from .platforms import build_checker

log = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))


async def run_once(settings: Settings) -> list[Result]:
    sem = asyncio.Semaphore(settings.concurrency)
    tasks = []

    for plat_name in settings.enabled_platforms():
        checker = build_checker(plat_name, timeout=settings.timeout)
        for product in settings.products:
            for location in settings.locations:
                tasks.append(
                    _guarded(sem, settings.per_request_delay,
                             checker, product, location)
                )

    nested = await asyncio.gather(*tasks)
    results = [r for batch in nested for r in batch]
    return results


async def _guarded(sem, delay, checker, product, location) -> list[Result]:
    async with sem:
        res = await checker.check(product, location)
        if delay:
            await asyncio.sleep(delay)
        return res


def execute(settings: Settings) -> list[Result]:
    """Sync wrapper: run checks, decide on notification, send."""
    results = asyncio.run(run_once(settings))
    timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")

    should_send, reason = _should_notify(settings, results)
    log.info("Run complete: %d results. Notify=%s (%s)",
             len(results), should_send, reason)

    _save_state(settings, results)

    if should_send:
        message = format_report(results, timestamp)
        if settings.channel == "telegram":
            send_telegram(settings.telegram_token, settings.telegram_chat_id, message)
            log.info("Telegram notification sent.")
        else:
            log.warning("Unknown channel '%s'; printing instead:\n%s",
                        settings.channel, message)
    return results


def _should_notify(settings: Settings, results: list[Result]) -> tuple[bool, str]:
    mode = settings.notify_mode
    if mode == "always":
        return True, "mode=always"

    has_stock = any(r.status == Stock.IN_STOCK for r in results)
    if mode == "on_available":
        return has_stock, "in-stock found" if has_stock else "nothing in stock"

    if mode == "on_change":
        prev = _load_state(settings)
        cur = {r.key(): r.status.value for r in results}
        changed = cur != prev
        # always alert on a NEW in-stock regardless of other noise
        new_stock = any(
            r.status == Stock.IN_STOCK and prev.get(r.key()) != Stock.IN_STOCK.value
            for r in results
        )
        return (changed or new_stock), ("changed" if changed else "no change")

    return True, "unknown mode -> default send"


def _save_state(settings: Settings, results: list[Result]) -> None:
    snapshot = {r.key(): r.status.value for r in results}
    try:
        settings.state_file.write_text(json.dumps(snapshot, indent=2))
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not write state file: %s", exc)


def _load_state(settings: Settings) -> dict:
    try:
        return json.loads(settings.state_file.read_text())
    except Exception:
        return {}
