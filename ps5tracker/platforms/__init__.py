"""Platform registry."""

from __future__ import annotations

from .amazon import Amazon
from .bigbasket import BigBasket
from .blinkit import Blinkit
from .flipkart import Flipkart
from .instamart import Instamart
from .zepto import Zepto

REGISTRY = {
    "blinkit": Blinkit,
    "zepto": Zepto,
    "instamart": Instamart,
    "bigbasket": BigBasket,
    "amazon": Amazon,
    "flipkart": Flipkart,
}


def build_checker(name: str, timeout: int):
    cls = REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"unknown platform '{name}' (known: {list(REGISTRY)})")
    return cls(timeout=timeout)
