from datetime import date
from pathlib import Path

from calendeal import middleware, snapshot
from calendeal.models import Deal
from calendeal.sources.slickdeals import parse_feed

FIXTURE = Path(__file__).parent / "fixtures" / "rss_sample.xml"


def test_rss_parsing():
    deals = parse_feed(FIXTURE.read_text())
    assert len(deals) == 2
    tide, sony = deals
    assert tide.store == "Amazon" and tide.category == "grocery" and tide.channel == "online"
    assert tide.start == date(2026, 11, 21) and tide.end > tide.start
    assert sony.store == "Best Buy" and sony.promo_code == "SAVE20NOW" and sony.category == "electronics"
    assert "<b>" not in tide.description


def test_check_links_uses_cache_and_throttles(tmp_path, monkeypatch):
    monkeypatch.setattr(middleware, "CACHE", tmp_path / "cache.json")
    calls, sleeps = [], []
    monkeypatch.setattr(middleware, "_vt_lookup", lambda url, key: calls.append(url) or ("bad" not in url))
    t = date(2026, 11, 22)
    ds = [Deal(f"D{i}", "S", t, t, url=f"https://site{i}.example") for i in range(5)]
    ds.append(Deal("Bad", "S", t, t, url="https://bad.example"))
    middleware.check_links(ds, key="k", sleep=sleeps.append)
    assert len(calls) == 6 and sleeps == [61]          # 4 per minute
    assert [d.link_safe for d in ds][-1] is False
    calls.clear()
    middleware.check_links(ds, key="k", sleep=sleeps.append)
    assert calls == []                                  # second run is all cache


def test_check_links_without_key_leaves_unverified(tmp_path, monkeypatch):
    monkeypatch.setattr(middleware, "CACHE", tmp_path / "cache.json")
    monkeypatch.delenv("VIRUSTOTAL_API_KEY", raising=False)
    t = date(2026, 11, 22)
    d = Deal("A", "S", t, t, url="https://x.example")
    middleware.check_links([d])
    assert d.link_safe is None


def test_snapshot_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "SNAP_DIR", tmp_path)
    t = date(2026, 11, 22)
    dup = Deal("A", "S", t, t, promo_code="Z")
    path = snapshot.save([dup, dup, Deal("B", "S", t, t)], taken=t)
    assert path.name == "2026-11-22.json"
    loaded = snapshot.load("latest")
    assert len(loaded) == 2 and loaded[0].promo_code == "Z"
