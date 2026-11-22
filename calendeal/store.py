"""Per-user state on disk: profile, the deals on their CalenDeal calendar, and deals they dismissed.

    data/users/<user>/profile.json
    data/users/<user>/calendar.json     deals currently on their calendar
    data/users/<user>/dismissed.json    deal ids they swiped away (never suggest again)
    data/users/<user>/calendeal.ics     regenerated on every change

Because the calendar file is rebuilt from calendar.json, removing a deal here removes it from the
calendar too (for imports: re-import; for a hosted .ics URL: subscribers update automatically).
data/users/ is git-ignored: it's per-person.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path

from calendeal.ics import write_ics
from calendeal.models import Deal, UserProfile

ROOT = Path(__file__).resolve().parents[1]
USERS = ROOT / "data" / "users"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "user"


def user_dir(user: str) -> Path:
    d = USERS / slug(user)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


# ---------- profile ----------

def save_profile(profile: UserProfile) -> Path:
    path = user_dir(profile.name) / "profile.json"
    path.write_text(json.dumps(asdict(profile), indent=1))
    return path


def load_profile(user: str) -> UserProfile | None:
    data = _read(USERS / slug(user) / "profile.json", None)
    return UserProfile(**data) if data else None


def list_users() -> list[str]:
    if not USERS.exists():
        return []
    return sorted(p.parent.name for p in USERS.glob("*/profile.json"))


# ---------- calendar ----------

def calendar(user: str) -> list[Deal]:
    return [Deal.from_dict(d) for d in _read(user_dir(user) / "calendar.json", [])]


def _save_calendar(user: str, deals: list[Deal]) -> Path:
    d = user_dir(user)
    (d / "calendar.json").write_text(json.dumps([x.to_dict() | {"reason": x.reason} for x in deals], indent=1))
    return write_ics(sorted(deals, key=lambda x: x.start), d / "calendeal.ics")


def ics_path(user: str) -> Path:
    path = user_dir(user) / "calendeal.ics"
    if not path.exists():
        _save_calendar(user, calendar(user))
    return path


def add(user: str, deals: list[Deal], limit: int | None = None) -> list[Deal]:
    """Add deals (skipping duplicates and dismissed ones). Respects the weekly limit if given."""
    current = calendar(user)
    have = {d.deal_id for d in current}
    gone = dismissed(user)
    added = []
    for d in deals:
        if d.deal_id in have or d.deal_id in gone:
            continue
        if limit is not None and len(current) >= limit:
            break
        current.append(d)
        have.add(d.deal_id)
        added.append(d)
    _save_calendar(user, current)
    return added


def remove(user: str, deal_id: str, dismiss: bool = True) -> bool:
    current = calendar(user)
    keep = [d for d in current if d.deal_id != deal_id]
    if dismiss:
        ids = dismissed(user) | {deal_id}
        (user_dir(user) / "dismissed.json").write_text(json.dumps(sorted(ids)))
    _save_calendar(user, keep)
    return len(keep) != len(current)


def clear(user: str) -> None:
    _save_calendar(user, [])


def dismissed(user: str) -> set[str]:
    return set(_read(user_dir(user) / "dismissed.json", []))
