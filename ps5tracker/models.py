"""Shared data structures."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class Stock(str, Enum):
    """Availability status for a single product on a single platform/location."""

    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    NOT_LISTED = "not_listed"      # platform doesn't carry the product at all
    UNKNOWN = "unknown"            # we couldn't determine (e.g. scrape failed)
    ERROR = "error"                # the check itself blew up


@dataclass
class Product:
    name: str
    query: str
    match: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)

    def title_matches(self, title: str) -> bool:
        """True if a result title belongs to this product."""
        t = title.lower()
        if any(x in t for x in self.exclude):
            return False
        return all(m in t for m in self.match) if self.match else True


@dataclass
class Location:
    name: str
    pincode: str
    lat: Optional[float] = None
    lon: Optional[float] = None


@dataclass
class Result:
    """Outcome of checking one product on one platform at one location."""

    platform: str
    product: str
    location: str
    pincode: str
    status: Stock
    title: Optional[str] = None       # matched listing title, if any
    price: Optional[str] = None       # raw price string as shown
    url: Optional[str] = None         # link to the product/listing
    eta: Optional[str] = None         # delivery ETA (quick-commerce)
    note: Optional[str] = None        # error detail / extra context

    def key(self) -> str:
        """Stable identity used for change detection."""
        return f"{self.platform}|{self.product}|{self.pincode}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d
