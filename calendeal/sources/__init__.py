"""Deal sources. Each module exposes `fetch() -> list[Deal]`.

To add one: copy sample.py, write fetch(), then add it to SOURCES below.
"""
from calendeal.models import Deal
from calendeal.sources import sample

SOURCES = [
    sample,
    # maverik,
    # old_navy,
]


def fetch_all() -> list[Deal]:
    deals: list[Deal] = []
    for src in SOURCES:
        try:
            found = src.fetch()
            for d in found:
                d.source = d.source or src.__name__.rsplit(".", 1)[-1]
            deals.extend(found)
        except Exception as e:  # one broken scraper shouldn't kill the run
            print(f"[warn] {src.__name__} failed: {e}")
    return deals
