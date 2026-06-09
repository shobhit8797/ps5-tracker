"""Base class and shared helpers for platform checkers.

Each platform implements `check(product, location) -> list[Result]`. The base
class wraps every check in error handling so one broken scraper never sinks the
whole run — a failure becomes a Result with status=ERROR instead of an
exception.
"""

from __future__ import annotations

import abc
import logging

from ..models import Location, Product, Result, Stock

log = logging.getLogger(__name__)

# A realistic desktop Chrome UA. Quick-commerce sites reject obvious bots.
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class PlatformChecker(abc.ABC):
    """Subclass and implement `name` + `_check`."""

    name: str = "base"
    #: quick-commerce platforms need lat/lon; set False for pincode-only sites
    requires_geo: bool = True

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def check(self, product: Product, location: Location) -> list[Result]:
        """Public entrypoint — never raises."""
        if self.requires_geo and (location.lat is None or location.lon is None):
            return [
                self._result(
                    product,
                    location,
                    Stock.UNKNOWN,
                    note="location missing lat/lon (required for quick-commerce)",
                )
            ]
        try:
            results = await self._check(product, location)
            return results or [
                self._result(product, location, Stock.NOT_LISTED)
            ]
        except Exception as exc:  # noqa: BLE001 — isolate scraper failures
            log.warning("[%s] check failed for %s @ %s: %s",
                        self.name, product.name, location.name, exc)
            return [self._result(product, location, Stock.ERROR, note=str(exc))]

    @abc.abstractmethod
    async def _check(self, product: Product, location: Location) -> list[Result]:
        ...

    # -- helpers -------------------------------------------------------------

    def _result(
        self,
        product: Product,
        location: Location,
        status: Stock,
        **kw,
    ) -> Result:
        return Result(
            platform=self.name,
            product=product.name,
            location=location.name,
            pincode=location.pincode,
            status=status,
            **kw,
        )
