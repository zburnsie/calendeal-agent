"""The weekly "mega scrape": run every source once, save the result, and match against the saved copy.

Matching every demo profile against one saved snapshot keeps the demo reproducible and keeps us
inside the free API limits (VirusTotal especially).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from calendeal.models import Deal

ROOT = Path(__file__).resolve().parents[1]
SNAP_DIR = ROOT / "data" / "snapshots"


def save(deals: list[Deal], taken: date | None = None) -> Path:
    taken = taken or date.today()
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    unique = {d.deal_id: d for d in deals}  # same deal from two sources -> keep one
    path = SNAP_DIR / f"{taken.isoformat()}.json"
    path.write_text(json.dumps(
        {"taken": taken.isoformat(), "count": len(unique), "deals": [d.to_dict() for d in unique.values()]},
        indent=1,
    ))
    return path


def resolve(name: str) -> Path:
    """'latest', a date like '2026-11-23', or a path."""
    if name == "latest":
        snaps = sorted(SNAP_DIR.glob("*.json"))
        if not snaps:
            raise SystemExit("No snapshots yet. Run: python -m calendeal.main snapshot")
        return snaps[-1]
    p = Path(name)
    return p if p.exists() else SNAP_DIR / f"{name}.json"


def load(name: str = "latest") -> list[Deal]:
    data = json.loads(resolve(name).read_text())
    return [Deal.from_dict(d) for d in data["deals"]]
