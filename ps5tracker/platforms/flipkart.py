"""Flipkart checker (headless browser).

Flipkart renders search server-side but aggressively blocks plain HTTP, so we
use headless Chromium. Flipkart's CSS class names are obfuscated and rotate, so
we match structurally (anchors that link to /p/ product pages) rather than
relying on a single class name. Verify on flipkart.com if matching breaks.
"""

from __future__ import annotations

import urllib.parse

from ..models import Location, Product, Result, Stock
from .base import DEFAULT_UA, PlatformChecker


class Flipkart(PlatformChecker):
    name = "flipkart"
    requires_geo = False  # pincode checked on product page; search is national

    async def _check(self, product: Product, location: Location) -> list[Result]:
        # Imported lazily so API-only users don't need Playwright installed.
        from playwright.async_api import async_playwright

        q = urllib.parse.quote_plus(product.query)
        url = f"https://www.flipkart.com/search?q={q}"

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent=DEFAULT_UA,
                locale="en-IN",
                viewport={"width": 1366, "height": 900},
            )
            page = await ctx.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded",
                                timeout=self.timeout * 1000)
                # dismiss the login modal if it appears
                try:
                    await page.click("button._2KpZ6l._2doB4z", timeout=3000)
                except Exception:
                    pass

                await page.wait_for_selector("a[href*='/p/']", timeout=self.timeout * 1000)
                cards = await page.query_selector_all("a[href*='/p/']")

                seen = set()
                results = []
                for card in cards:
                    title = (await card.get_attribute("title")) or (await card.inner_text())
                    title = (title or "").strip().split("\n")[0]
                    if not title or title in seen or not product.title_matches(title):
                        continue
                    seen.add(title)

                    href = await card.get_attribute("href")
                    full_url = f"https://www.flipkart.com{href}" if href and href.startswith("/") else href

                    # price/stock live near the card; read the enclosing container text
                    container = await card.evaluate_handle(
                        "el => el.closest('div[data-id]') || el.parentElement.parentElement"
                    )
                    text = (await container.inner_text()).lower() if container else ""

                    if "sold out" in text or "out of stock" in text or "coming soon" in text:
                        status = Stock.OUT_OF_STOCK
                    elif "₹" in text:
                        status = Stock.IN_STOCK
                    else:
                        status = Stock.UNKNOWN

                    price = None
                    if "₹" in text:
                        # crude: grab first ₹-prefixed token
                        frag = text[text.index("₹"):]
                        price = "₹" + "".join(
                            c for c in frag[1:14] if c.isdigit() or c == ","
                        )

                    results.append(
                        self._result(product, location, status,
                                     title=title, price=price, url=full_url)
                    )
                    break
                return results
            finally:
                await ctx.close()
                await browser.close()
