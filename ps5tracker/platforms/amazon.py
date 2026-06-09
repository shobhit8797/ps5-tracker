"""Amazon India checker (headless browser).

Amazon serves search via HTML and blocks plain HTTP clients quickly, so we drive
a headless Chromium. We set the delivery pincode where possible and read the
first matching search card. Selectors reflect amazon.in as of writing.
"""

from __future__ import annotations

import asyncio
import urllib.parse

from ..models import Location, Product, Result, Stock
from .base import DEFAULT_UA, PlatformChecker


class Amazon(PlatformChecker):
    name = "amazon"
    requires_geo = False  # pincode only

    async def _check(self, product: Product, location: Location) -> list[Result]:
        # Imported lazily so API-only users don't need Playwright installed.
        from playwright.async_api import async_playwright

        q = urllib.parse.quote_plus(product.query)
        url = f"https://www.amazon.in/s?k={q}"

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent=DEFAULT_UA,
                locale="en-IN",
                viewport={"width": 1366, "height": 900},
            )
            page = await ctx.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                await _maybe_set_pincode(page, location.pincode)
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                await page.wait_for_selector("div[data-component-type='s-search-result']",
                                             timeout=self.timeout * 1000)
                cards = await page.query_selector_all(
                    "div[data-component-type='s-search-result']"
                )
                results = []
                for card in cards[:15]:
                    title_el = await card.query_selector("h2 span")
                    title = (await title_el.inner_text()).strip() if title_el else ""
                    if not title or not product.title_matches(title):
                        continue

                    link_el = await card.query_selector("h2 a")
                    href = await link_el.get_attribute("href") if link_el else None
                    full_url = f"https://www.amazon.in{href}" if href and href.startswith("/") else href

                    price_el = await card.query_selector("span.a-price > span.a-offscreen")
                    price = (await price_el.inner_text()).strip() if price_el else None

                    text = (await card.inner_text()).lower()
                    if "currently unavailable" in text or "out of stock" in text:
                        status = Stock.OUT_OF_STOCK
                    elif price:
                        status = Stock.IN_STOCK
                    else:
                        status = Stock.UNKNOWN

                    results.append(
                        self._result(product, location, status,
                                     title=title, price=price, url=full_url)
                    )
                    break  # first matching card is enough
                return results
            finally:
                await ctx.close()
                await browser.close()


async def _maybe_set_pincode(page, pincode: str) -> None:
    """Best-effort: open the location popover and enter the pincode."""
    try:
        await page.click("#nav-global-location-popover-link", timeout=5000)
        await page.fill("#GLUXZipUpdateInput", pincode, timeout=5000)
        await page.click("#GLUXZipUpdate input[type='submit'], #GLUXZipUpdate-announce",
                         timeout=5000)
        await asyncio.sleep(1.5)
    except Exception:
        # location widget changes often; proceed with default location
        pass
