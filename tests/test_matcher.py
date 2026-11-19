from datetime import date

from calendeal.gcal import to_event
from calendeal.matcher import retrieve
from calendeal.models import Deal, UserProfile
from calendeal.sources import fetch_all


def profile(**kw):
    base = dict(name="t", interests=["pizza", "hot drinks"], stores=["Maverik"], avoid=["grocery"])
    base.update(kw)
    return UserProfile(**base)


def test_sample_source_loads():
    assert len(fetch_all()) > 0


def test_avoid_filters_out_deals():
    picks = retrieve(fetch_all(), profile())
    assert all("grocery" not in d.category for d in picks)


def test_relevant_deals_rank_first():
    picks = retrieve(fetch_all(), profile())
    assert picks[0].store == "Maverik" or "pizza" in picks[0].title.lower()


def test_deal_id_is_stable():
    a = Deal("X", "Y", date(2026, 11, 1), date(2026, 11, 1))
    b = Deal("X", "Y", date(2026, 11, 1), date(2026, 11, 3))
    assert a.deal_id == b.deal_id


def test_all_day_event_end_is_exclusive():
    d = Deal("Sale", "Store", date(2026, 11, 25), date(2026, 11, 29))
    ev = to_event(d)
    assert ev["start"]["date"] == "2026-11-25"
    assert ev["end"]["date"] == "2026-11-30"
