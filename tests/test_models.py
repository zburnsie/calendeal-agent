from datetime import date

import pytest

from calendeal.models import Deal, UserProfile


def test_deal_id_is_stable():
    a = Deal("X", "Y", date(2026, 11, 1), date(2026, 11, 1))
    b = Deal("X", "Y", date(2026, 11, 1), date(2026, 11, 3))
    assert a.deal_id == b.deal_id


def test_deal_roundtrip_ignores_unknown_keys():
    d = Deal("X", "Y", date(2026, 11, 1), date(2026, 11, 2), promo_code="ABC")
    data = d.to_dict() | {"something_new": 1}
    assert Deal.from_dict(data).promo_code == "ABC"


def test_hitl_mode_validated():
    with pytest.raises(ValueError):
        UserProfile(name="x", hitl_mode="sometimes")


def test_weekly_limit_capped():
    assert UserProfile(name="x", max_deals_per_week=500).max_deals_per_week == 20
