"""Shared data types. Every source, the matcher, and gcal.py speak in these."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class Deal:
    title: str                 # "Free hot cocoa"
    store: str                 # "Maverik"
    start: date
    end: date                  # inclusive; same as start for one-day deals
    description: str = ""
    category: str = ""         # food, clothing, electronics, entertainment...
    channel: str = "in store"  # "in store", "online", "in store & online"
    url: str = ""
    location: str = ""
    source: str = ""           # which scraper found it

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
        return f"{self.title}. {self.store}. {self.category}. {self.channel}. {self.description}"

    @classmethod
    def from_dict(cls, d: dict) -> "Deal":
        d = dict(d)
        d["start"] = date.fromisoformat(d["start"])
        d["end"] = date.fromisoformat(d.get("end") or d["start"].isoformat())
        return cls(**d)


@dataclass
class UserProfile:
    name: str
    interests: list[str]                       # free text works best: "cheap pizza", "running shoes"
    stores: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    location: str = ""
    prefers_online: bool = False
    max_deals_per_week: int = 8

    def text(self) -> str:
        parts = self.interests + self.stores
        if self.prefers_online:
            parts.append("online")
        return ". ".join(parts)

    @classmethod
    def load(cls, path: str | Path) -> "UserProfile":
        return cls(**json.loads(Path(path).read_text()))
