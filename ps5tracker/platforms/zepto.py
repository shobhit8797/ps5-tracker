"""Zepto checker (internal search API).

Zepto resolves a `storeId` from lat/lon, then searches within that store. We do
both calls. Endpoints reflect Zepto's web client as of writing — verify via
DevTools → Network on zeptonow.com if results dry up.
"""

from __future__ import annotations

import httpx

from ..models import Location, Product, Result, Stock
from .base import DEFAULT_UA, PlatformChecker

STORE_URL = "https://api.zeptonow.com/api/v1/config/layout"
SEARCH_URL = "https://api.zeptonow.com/api/v3/search"


class Zepto(PlatformChecker):
    name = "zepto"
    requires_geo = True

    async def _check(self, product: Product, location: Location) -> list[Result]:
        headers = {
            "User-Agent": DEFAULT_UA,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "app_sub_platform": "WEB",
            "appVersion": "12.39.1",
            "Referer": "https://www.zeptonow.com/",
        }
        async with httpx.AsyncClient(timeout=self.timeout, http2=True) as client:
            # 1. resolve store for these coordinates
            store_resp = await client.get(
                STORE_URL,
                headers=headers,
                params={"latitude": location.lat, "longitude": location.lon},
            )
            store_resp.raise_for_status()
            store_id = _extract_store_id(store_resp.json())
            if not store_id:
                return [
                    self._result(product, location, Stock.UNKNOWN,
                                 note="could not resolve Zepto store for coords")
                ]

            # 2. search within the store
            search_headers = {**headers, "store_id": store_id, "storeId": store_id}
            search_resp = await client.post(
                SEARCH_URL,
                headers=search_headers,
                json={
                    "query": product.query,
                    "pageNumber": 0,
                    "storeId": store_id,
                    "mode": "AUTOSUGGEST",
                },
            )
            search_resp.raise_for_status()
            return _parse(self, product, location, search_resp.json())


def _extract_store_id(data: dict) -> str | None:
    for key in ("storeId", "store_id"):
        if key in data:
            return str(data[key])
    # sometimes nested under storeServiceability / stores[]
    sid = data.get("storeServiceability", {}).get("storeId")
    if sid:
        return str(sid)
    stores = data.get("stores")
    if isinstance(stores, list) and stores:
        return str(stores[0].get("storeId") or stores[0].get("id"))
    return None


def _parse(checker, product: Product, location: Location, data: dict) -> list[Result]:
    out: list[Result] = []
    items = _collect_products(data)
    for it in items:
        title = it.get("name") or it.get("productName") or ""
        if not title or not product.title_matches(title):
            continue
        out_of_stock = it.get("outOfStock", False) or it.get("availableQuantity", 1) == 0
        price = it.get("sellingPrice") or it.get("mrp") or it.get("price")
        if isinstance(price, (int, float)) and price > 1000:
            price = price / 100  # Zepto often stores paise
        out.append(
            checker._result(
                product, location,
                Stock.OUT_OF_STOCK if out_of_stock else Stock.IN_STOCK,
                title=title,
                price=f"₹{price}" if price else None,
                url="https://www.zeptonow.com/",
                eta=None if out_of_stock else "~10 min",
            )
        )
    return out


def _collect_products(node, acc=None) -> list[dict]:
    if acc is None:
        acc = []
    if isinstance(node, dict):
        if ("name" in node or "productName" in node) and (
            "sellingPrice" in node or "mrp" in node or "outOfStock" in node
        ):
            acc.append(node)
        for v in node.values():
            _collect_products(v, acc)
    elif isinstance(node, list):
        for v in node:
            _collect_products(v, acc)
    return acc
