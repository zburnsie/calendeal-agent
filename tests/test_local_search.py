from datetime import date

from calendeal.sources import local_search
from calendeal.sources.local_search import FoundDeal, FoundDeals
from tests.fakes import StubStructured

TODAY = date(2026, 11, 22)
RESULTS = [
    {"title": "Cafe X BOGO bowls", "url": "https://cafex.example/deals", "snippet": "BOGO bowls through Nov 28"},
    {"title": "Top 10 deals", "url": "https://listicle.example", "snippet": "..."},
]


def test_extract_keeps_only_cited_urls_and_fills_dates():
    found = FoundDeals(deals=[
        FoundDeal(title="BOGO bowls", store="Cafe X", url="https://cafex.example/deals", end="2026-11-28"),
        FoundDeal(title="Made up", store="Nowhere", url="https://invented.example"),
    ])
    deals = local_search.extract(RESULTS, "food", "Provo, UT", TODAY, model=StubStructured(found))
    assert [d.title for d in deals] == ["BOGO bowls"]
    d = deals[0]
    assert d.start == TODAY and d.end == date(2026, 11, 28)
    assert d.category == "food" and d.source == "local_search" and d.location == "Provo, UT"


def test_search_runs_each_query_and_skips_failures():
    seen = []

    def searcher(q):
        seen.append(q)
        if "car wash" in q:
            raise RuntimeError("network")
        return RESULTS

    found = FoundDeals(deals=[FoundDeal(title="BOGO bowls", store="Cafe X", url="https://cafex.example/deals")])
    deals = local_search.search(["car"], "Provo, UT", extra="cheap tires", today=TODAY,
                                model=StubStructured(found), searcher=searcher)
    assert seen[0] == "cheap tires Provo, UT" and len(seen) == 3
    assert len(deals) == 2  # oil change query + extra query; car wash failed


def test_fetch_off_by_default(monkeypatch):
    monkeypatch.delenv("CALENDEAL_LOCAL_SEARCH", raising=False)
    assert local_search.fetch() == []
