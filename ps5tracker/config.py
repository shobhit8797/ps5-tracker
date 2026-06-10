"""Load and validate config.yaml + .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .models import Location, Product

ROOT = Path(__file__).resolve().parent.parent


def _default_config_path() -> Path:
    cwd_config = Path.cwd() / "config.yaml"
    if cwd_config.exists():
        return cwd_config
    return ROOT / "config.yaml"


@dataclass
class Settings:
    products: list[Product]
    locations: list[Location]
    platforms: dict[str, dict]
    notify_mode: str
    channel: str
    per_request_delay: float
    concurrency: int
    timeout: int
    state_file: Path
    telegram_token: str
    telegram_chat_id: str

    def enabled_platforms(self) -> list[str]:
        return [name for name, cfg in self.platforms.items() if cfg.get("enabled", True)]


def load_settings(config_path: str | Path | None = None) -> Settings:
    resolved_config = Path(config_path) if config_path else _default_config_path()
    resolved_config = resolved_config.expanduser().resolve()
    config_dir = resolved_config.parent
    load_dotenv(config_dir / ".env")

    with open(resolved_config, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    products = [
        Product(
            name=p["name"],
            query=p["query"],
            match=[m.lower() for m in p.get("match", [])],
            exclude=[x.lower() for x in p.get("exclude", [])],
        )
        for p in raw.get("products", [])
    ]

    locations = [
        Location(
            name=l["name"],
            pincode=str(l["pincode"]),
            lat=l.get("lat"),
            lon=l.get("lon"),
        )
        for l in raw.get("locations", [])
    ]

    rt = raw.get("runtime", {})
    notif = raw.get("notifications", {})

    if not products:
        raise ValueError("config.yaml: no products defined")
    if not locations:
        raise ValueError("config.yaml: no locations defined")

    state_file = Path(rt.get("state_file", "state.json"))
    if not state_file.is_absolute():
        state_file = config_dir / state_file

    return Settings(
        products=products,
        locations=locations,
        platforms=raw.get("platforms", {}),
        notify_mode=notif.get("notify_mode", "always"),
        channel=notif.get("channel", "telegram"),
        per_request_delay=float(rt.get("per_request_delay", 2.0)),
        concurrency=int(rt.get("concurrency", 3)),
        timeout=int(rt.get("timeout", 30)),
        state_file=state_file,
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
    )
