"""Shared data types. Every source, the middleware, the matcher, and the calendar writers speak in these."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, fields
from datetime import date
from pathlib import Path

# Intake checkbox categories (Pinterest-style). Sources should map deals onto these.
CATEGORIES = [
    "food",           # restaurants, fast food, coffee
    "grocery",        # groceries + household staples
    "clothing",
    "electronics",
    "entertainment",  # movies, events, activities
    "car",            # oil change, car wash, gas
    "home",
    "health & beauty",
    "gifts",
    "shopping",       # general / online / sitewide sales
]

HITL_MODES = ("auto", "approve")
MAX_DEALS_CAP = 20


@dataclass
class Deal:
    title: str                 # "Free hot cocoa"
    store: str                 # "Maverik"
    start: date
    end: date                  # inclusive; same as start for one-day deals
    description: str = ""
    category: str = ""         # one of CATEGORIES when possible
    channel: str = "in store"  # "in store", "online", "in store & online"
    url: str = ""
    location: str = ""         # city or address for in-store deals
    promo_code: str = ""       # shown in the calendar event so you don't hunt for it at checkout
    brand: str = ""            # "Tide"
    product_type: str = ""     # "detergent" — lets brand-loyal matching work
    source: str = ""           # which source found it

    # filled in by middleware
    link_safe: bool | None = None   # None = not checked

    # filled in by the matcher
    score: float = 0.0
    reason: str = ""

    @property
    def deal_id(self) -> str:
        """Stable id so we never add the same deal twice."""
        key = f"{self.store}|{self.title}|{self.start.isoformat()}".lower()
        return hashlib.sha1(key.encode()).hexdigest()[:16]

    def text(self) -> str:
        """What the retriever embeds/indexes."""
        parts = [self.title, self.store, self.category, self.channel, self.brand, self.product_type, self.description]
        return ". ".join(p for p in parts if p)

    def is_expired(self, today: date | None = None) -> bool:
        return self.end < (today or date.today())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start"] = self.start.isoformat()
        d["end"] = self.end.isoformat()
        d.pop("score", None)
        d.pop("reason", None)
        return d

    def short(self) -> str:
        """One line for chat/tool output."""
        code = f" · code {self.promo_code}" if self.promo_code else ""
        when = f"{self.start:%a %b %d}" + (f"–{self.end:%b %d}" if self.end != self.start else "")
        return f"[{self.deal_id}] {self.title} @ {self.store} ({self.category}, {self.channel}, {when}){code}"

    @classmethod
    def from_dict(cls, d: dict) -> "Deal":
        known = {f.name for f in fields(cls)}
        d = {k: v for k, v in d.items() if k in known}
        d["start"] = date.fromisoformat(d["start"])
        d["end"] = date.fromisoformat(d.get("end") or d["start"].isoformat())
        return cls(**d)


@dataclass
class UserProfile:
    name: str
    interests: list[str] = field(default_factory=list)   # free text works best: "cheap pizza", "running shoes"
    categories: list[str] = field(default_factory=list)  # intake checkboxes; empty = all categories
    stores: list[str] = field(default_factory=list)      # favorite stores get a boost
    avoid: list[str] = field(default_factory=list)       # words/categories to never show
    brand_loyal: dict[str, str] = field(default_factory=dict)  # {"detergent": "Tide"}: only Tide for detergent; anything not listed = any brand
    notes: str = ""                                      # free-text intake: "looking for Black Friday TVs"
    location: str = ""                                   # city or ZIP, not a street address
    radius_miles: int = 15
    prefers_online: bool = False
    hitl_mode: str = "approve"                           # "auto" = straight to calendar, "approve" = user taps first
    max_deals_per_week: int = 8

    def __post_init__(self) -> None:
        if self.hitl_mode not in HITL_MODES:
            raise ValueError(f"hitl_mode must be one of {HITL_MODES}, got {self.hitl_mode!r}")
        self.max_deals_per_week = max(1, min(int(self.max_deals_per_week), MAX_DEALS_CAP))
        self.categories = [c.lower() for c in self.categories]

    def text(self) -> str:
        parts = self.interests + self.categories + self.stores
        parts += [f"{brand} {product}" for product, brand in self.brand_loyal.items()]
        if self.notes:
            parts.append(self.notes)
        if self.prefers_online:
            parts.append("online")
        return ". ".join(parts)

    @classmethod
    def load(cls, path: str | Path) -> "UserProfile":
        return cls(**json.loads(Path(path).read_text()))
