"""Swiggy Instamart checker (internal search API).

Instamart is part of Swiggy and serves by lat/lon supplied as cookies/headers.
Endpoints reflect Swiggy's web client as of writing.
"""

from __future__ import annotations

import httpx

from ..models import Location, Product, Result, Stock
from .base import DEFAULT_UA, PlatformChecker

SEARCH_URL = "https://www.swiggy.com/api/instamart/search"


class Instamart(PlatformChecker):
    name = "instamart"
    requires_geo = True

    async def _check(self, product: Product, location: Location) -> list[Result]:
        headers = {
            "User-Agent": DEFAULT_UA,
            "Accept": "application/json",
            "Referer": "https://www.swiggy.com/instamart",
        }
        cookies = {
            # Swiggy reads the active delivery location from these cookies.
            "lat": str(location.lat),
            "lng": str(location.lon),
            "userLocation": (
                f'{{"lat":{location.lat},"lng":{location.lon},'
                f'"address":"","pincode":"{location.pincode}"}}'
            ),
        }
        params = {
            "query": product.query,
            "pageNumber": 0,
            "searchResultsOffset": 0,
            "limit": 40,
        }
        async with httpx.AsyncClient(timeout=self.timeout, http2=True) as client:
            resp = await client.get(
                SEARCH_URL, headers=headers, cookies=cookies, params=params
            )
            resp.raise_for_status()
            return _parse(self, product, location, resp.json())


def _parse(checker, product: Product, location: Location, data: dict) -> list[Result]:
    out: list[Result] = []
    for variation in _collect_variations(data):
        title = variation.get("display_name") or variation.get("name") or ""
        if not title or not product.title_matches(title):
            continue
        avail = variation.get("inventory", {}).get("in_stock")
        if avail is None:
            avail = not variation.get("out_of_stock", False)
        price_info = variation.get("price", {})
        price = price_info.get("offer_price") or price_info.get("mrp")
        out.append(
            checker._result(
                product, location,
                Stock.IN_STOCK if avail else Stock.OUT_OF_STOCK,
                title=title,
                price=f"₹{price}" if price else None,
                url="https://www.swiggy.com/instamart",
                eta="~15 min" if avail else None,
            )
        )
    return out


def _collect_variations(node, acc=None) -> list[dict]:
    if acc is None:
        acc = []
    if isinstance(node, dict):
        if ("display_name" in node or "name" in node) and (
            "price" in node or "inventory" in node or "out_of_stock" in node
        ):
            acc.append(node)
        for v in node.values():
            _collect_variations(v, acc)
    elif isinstance(node, list):
        for v in node:
            _collect_variations(v, acc)
    return acc
