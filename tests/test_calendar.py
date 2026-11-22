from datetime import date

from calendeal.ics import build_ics
from calendeal.models import Deal


def deal(**kw):
    base = dict(title="Sale", store="Store", start=date(2026, 11, 25), end=date(2026, 11, 29))
    base.update(kw)
    return Deal(**base)


def test_ics_all_day_end_is_exclusive():
    text = build_ics([deal()])
    assert "DTSTART;VALUE=DATE:20261125" in text
    assert "DTEND;VALUE=DATE:20261130" in text


def test_ics_has_promo_code_reminder_and_uid():
    d = deal(promo_code="SAVE20", url="https://example.com", reason="you buy shoes")
    text = build_ics([d]).replace("\r\n ", "")  # unfold
    assert "Promo code: SAVE20" in text
    assert "BEGIN:VALARM" in text
    assert f"UID:{d.deal_id}@calendeal" in text


def test_ics_escapes_and_folds():
    text = build_ics([deal(description="Commas, semicolons; and a very long line " * 5)])
    assert "\\," in text and "\;" in text
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))
    assert text.startswith("BEGIN:VCALENDAR") and text.rstrip().endswith("END:VCALENDAR")


def test_gcal_event_matches():
    import pytest

    pytest.importorskip("googleapiclient")
    from calendeal.gcal import to_event

    ev = to_event(deal(promo_code="X1"))
    assert ev["end"]["date"] == "2026-11-30"
    assert "Promo code: X1" in ev["description"]
