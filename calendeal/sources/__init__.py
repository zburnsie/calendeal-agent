"""Deal sources. Each module exposes `fetch() -> list[Deal]`.

To add one: copy sample.py, write fetch(), then add it to SOURCES below.
Prefer an API or RSS feed over scraping (docs/DATA_SOURCES.md).
"""
from calendeal.models import Deal
from calendeal.sources import local_search, sample, slickdeals

SOURCES = {
    "sample": sample,             # hand-entered deals (data/sample_deals.json), always works offline
    "slickdeals": slickdeals,     # national/online deals via RSS
    "local_search": local_search, # Provo/Utah deals via LLM web search (off until CALENDEAL_LOCAL_SEARCH=1)
}


def fetch_all(names: list[str] | None = None) -> list[Deal]:
    deals: list[Deal] = []
    for name, src in SOURCES.items():
        if names and name not in names:
            continue
        try:
            found = src.fetch()
            for d in found:
                d.source = d.source or name
            deals.extend(found)
            print(f"  {name}: {len(found)} deal(s)")
        except Exception as e:  # one broken source shouldn't kill the run
            print(f"[warn] {name} failed: {e}")
    return deals
