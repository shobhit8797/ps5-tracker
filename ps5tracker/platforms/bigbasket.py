"""BigBasket checker.

BigBasket (incl. BB Now / BB Daily) keys availability off a delivery pincode +
coordinates stored in cookies. Its listing service returns JSON. Endpoints
reflect BigBasket's web client as of writing.
"""

from __future__ import annotations

import httpx

from ..models import Location, Product, Result, Stock
from .base import DEFAULT_UA, PlatformChecker

SEARCH_URL = "https://www.bigbasket.com/listing-svc/v2/products"


class BigBasket(PlatformChecker):
    name = "bigbasket"
    requires_geo = True  # uses lat/lon cookie; pincode also sent

    async def _check(self, product: Product, location: Location) -> list[Result]:
        headers = {
            "User-Agent": DEFAULT_UA,
            "Accept": "application/json",
            "Referer": "https://www.bigbasket.com/ps/?q=" + product.query,
            "x-channel": "BB-WEB",
        }
        cookies = {
            "_bb_lat_long": f"{location.lat}|{location.lon}",
            "csurftoken": "",
            "_bb_pin_code": location.pincode,
        }
        params = {"type": "ps", "slug": product.query, "page": 1}
        async with httpx.AsyncClient(timeout=self.timeout, http2=True) as client:
            resp = await client.get(
                SEARCH_URL, headers=headers, cookies=cookies, params=params
            )
            resp.raise_for_status()
            return _parse(self, product, location, resp.json())


def _parse(checker, product: Product, location: Location, data: dict) -> list[Result]:
    out: list[Result] = []
    products = (
        data.get("tabs", [{}])[0]
        .get("product_info", {})
        .get("products", [])
        if data.get("tabs")
        else _collect(data)
    )
    if not products:
        products = _collect(data)

    for p in products:
        title = p.get("desc") or p.get("name") or ""
        if not title or not product.title_matches(title):
            continue
        avail = p.get("availability", {})
        in_stock = str(avail.get("avail_status", "")) == "001" or avail.get("display_name", "").lower().startswith("in stock")
        if not avail:
            in_stock = not p.get("sku_max_smart_basket", {}).get("out_of_stock", False)
        pricing = p.get("pricing", {}).get("discount", {})
        price = pricing.get("prim_price", {}).get("sp") or p.get("sp")
        slug = p.get("absolute_url") or p.get("slug")
        url = f"https://www.bigbasket.com{slug}" if slug and slug.startswith("/") else "https://www.bigbasket.com/"
        out.append(
            checker._result(
                product, location,
                Stock.IN_STOCK if in_stock else Stock.OUT_OF_STOCK,
                title=title,
                price=f"₹{price}" if price else None,
                url=url,
            )
        )
    return out


def _collect(node, acc=None) -> list[dict]:
    if acc is None:
        acc = []
    if isinstance(node, dict):
        if ("desc" in node or "name" in node) and ("pricing" in node or "availability" in node or "sp" in node):
            acc.append(node)
        for v in node.values():
            _collect(v, acc)
    elif isinstance(node, list):
        for v in node:
            _collect(v, acc)
    return acc
