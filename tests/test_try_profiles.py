from datetime import date

from calendeal.models import Deal, UserProfile
from scripts.try_profiles import check_picks, run

TODAY = date(2026, 11, 22)


def test_three_profiles_script_passes_offline():
    assert run(retriever="tfidf", use_llm=False, today=TODAY, quiet=True)


def test_checks_catch_bad_picks():
    p = UserProfile(name="x", categories=["food"], avoid=["beer"], brand_loyal={"detergent": "Tide"},
                    max_deals_per_week=2)
    bad = [
        Deal("Beer night", "Bar", TODAY, TODAY, category="food"),
        Deal("Gain $3 off", "Store", TODAY, TODAY, category="grocery", brand="Gain", product_type="detergent"),
        Deal("Old deal", "Store", date(2026, 11, 1), date(2026, 11, 2), category="food"),
        Deal("Scam TV", "Site", TODAY, TODAY, category="food", link_safe=False),
    ]
    failed = {name for name, ok, _ in check_picks(p, bad, TODAY) if not ok}
    assert failed == {"respects weekly limit", "only their categories", "never shows avoid list",
                      "brand loyalty respected", "no expired deals", "no flagged links"}
