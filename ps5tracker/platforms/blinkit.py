"""Blinkit checker (internal search API).

Blinkit serves results by lat/lon passed through headers. The endpoint and
header names below are based on Blinkit's web client as of writing; if results
stop coming through, open blinkit.com in your browser's DevTools → Network,
search for a product, and copy the updated request URL/headers here.
"""

from __future__ import annotations

import httpx

from ..models import Location, Product, Result, Stock
from .base import DEFAULT_UA, PlatformChecker

SEARCH_URL = "https://blinkit.com/v6/search/products"


class Blinkit(PlatformChecker):
    name = "blinkit"
    requires_geo = True

    async def _check(self, product: Product, location: Location) -> list[Result]:
        headers = {
            "User-Agent": DEFAULT_UA,
            "Accept": "application/json",
            "lat": str(location.lat),
            "lon": str(location.lon),
            "app_client": "consumer_web",
            "web_app_version": "1008010016",
            "Referer": "https://blinkit.com/",
        }
        params = {"q": product.query, "search_type": "type_to_search"}

        async with httpx.AsyncClient(timeout=self.timeout, http2=True) as client:
            resp = await client.get(SEARCH_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        return _parse(self, product, location, data)


def _parse(checker, product: Product, location: Location, data: dict) -> list[Result]:
    """Walk Blinkit's nested 'snippets' layout for product cards."""
    out: list[Result] = []
    snippets = _find_products(data)
    for prod in snippets:
        title = prod.get("name") or prod.get("display_name") or ""
        if not title or not product.title_matches(title):
            continue
        in_stock = not prod.get("is_sold_out", False) and prod.get("inventory", 1) != 0
        price = prod.get("price") or prod.get("mrp")
        pid = prod.get("product_id") or prod.get("id")
        url = f"https://blinkit.com/prn/x/prid/{pid}" if pid else "https://blinkit.com/"
        out.append(
            checker._result(
                product, location,
                Stock.IN_STOCK if in_stock else Stock.OUT_OF_STOCK,
                title=title,
                price=f"₹{price}" if price else None,
                url=url,
                eta="~10 min" if in_stock else None,
            )
        )
    return out


def _find_products(node, acc=None) -> list[dict]:
    """Blinkit nests product objects deep in the layout; collect anything that
    looks like a product card (has a name + price/inventory)."""
    if acc is None:
        acc = []
    if isinstance(node, dict):
        if ("name" in node or "display_name" in node) and (
            "price" in node or "inventory" in node or "is_sold_out" in node
        ):
            acc.append(node)
        for v in node.values():
            _find_products(v, acc)
    elif isinstance(node, list):
        for v in node:
            _find_products(v, acc)
    return acc
