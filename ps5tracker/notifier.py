"""Telegram notifications."""

from __future__ import annotations

import logging

import httpx

from .models import Result, Stock

log = logging.getLogger(__name__)

# Telegram messages cap at 4096 chars; keep a safety margin.
MAX_LEN = 3900

STATUS_EMOJI = {
    Stock.IN_STOCK: "✅",
    Stock.OUT_OF_STOCK: "❌",
    Stock.NOT_LISTED: "⚪️",
    Stock.UNKNOWN: "❔",
    Stock.ERROR: "⚠️",
}


def format_report(results: list[Result], timestamp: str) -> str:
    """Build a human-readable Telegram message grouped by product → location."""
    in_stock = [r for r in results if r.status == Stock.IN_STOCK]
    header = "🎮 *PS5 Availability Report*\n"
    header += f"_{timestamp}_\n"
    if in_stock:
        header += f"\n🔥 *{len(in_stock)} IN-STOCK hit(s)!*\n"
    header += "\n"

    # group by product, then location
    lines: list[str] = []
    by_product: dict[str, list[Result]] = {}
    for r in results:
        by_product.setdefault(r.product, []).append(r)

    for product, rows in by_product.items():
        lines.append(f"*{_esc(product)}*")
        by_loc: dict[str, list[Result]] = {}
        for r in rows:
            by_loc.setdefault(r.location, []).append(r)
        for loc, lrows in by_loc.items():
            lines.append(f"  📍 {_esc(loc)} ({lrows[0].pincode})")
            for r in sorted(lrows, key=lambda x: x.platform):
                emoji = STATUS_EMOJI.get(r.status, "❔")
                bit = f"    {emoji} {_esc(r.platform.title())}"
                extras = []
                if r.status == Stock.IN_STOCK:
                    if r.price:
                        extras.append(_esc(r.price))
                    if r.eta:
                        extras.append(_esc(r.eta))
                elif r.status == Stock.ERROR and r.note:
                    extras.append(_esc(r.note[:60]))
                if extras:
                    bit += " — " + " · ".join(extras)
                if r.status == Stock.IN_STOCK and r.url:
                    bit += f"\n      [🔗 buy]({r.url})"
                lines.append(bit)
        lines.append("")

    return header + "\n".join(lines)


def _esc(text: str) -> str:
    """Escape characters that break Telegram Markdown (legacy 'Markdown' mode)."""
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text


def send_telegram(token: str, chat_id: str, text: str) -> None:
    if not token or not chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID are not set. "
            "Copy .env.example to .env and fill them in."
        )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # split into chunks on line boundaries if too long
    for chunk in _chunk(text):
        resp = httpx.post(
            url,
            json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )
        if resp.status_code != 200:
            log.error("Telegram send failed: %s %s", resp.status_code, resp.text)
            resp.raise_for_status()


def _chunk(text: str) -> list[str]:
    if len(text) <= MAX_LEN:
        return [text]
    chunks, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > MAX_LEN:
            chunks.append(cur)
            cur = ""
        cur += line + "\n"
    if cur:
        chunks.append(cur)
    return chunks
