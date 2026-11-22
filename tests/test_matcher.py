from datetime import date

from calendeal.matcher import hard_filter, match, retrieve
from calendeal.models import Deal, UserProfile
from calendeal.sources import sample

TODAY = date(2026, 11, 22)


def deals():
    return sample.fetch()


def profile(**kw):
    base = dict(name="t", interests=["pizza", "hot drinks"], stores=["Maverik"], avoid=["grocery"])
    base.update(kw)
    return UserProfile(**base)


def test_sample_source_loads():
    assert len(deals()) > 0


def test_avoid_filters_out_deals():
    picks = retrieve(deals(), profile(), retriever="tfidf", today=TODAY)
    assert all("grocery" not in d.category for d in picks)


def test_relevant_deals_rank_first():
    picks = retrieve(deals(), profile(), retriever="tfidf", today=TODAY)
    assert picks[0].store == "Maverik" or "pizza" in picks[0].title.lower()


def test_expired_deals_never_returned():
    picks = retrieve(deals(), profile(avoid=[]), retriever="tfidf", today=TODAY)
    assert all(d.end >= TODAY for d in picks)
    assert not any("Expired" in d.title for d in picks)


def test_category_checkboxes_filter():
    picks = retrieve(deals(), profile(categories=["clothing"], avoid=[]), retriever="tfidf", today=TODAY)
    assert picks and all(d.category == "clothing" for d in picks)


def test_brand_loyal_drops_other_brands():
    p = profile(interests=["laundry detergent"], avoid=[], categories=["grocery"], brand_loyal={"detergent": "Tide"})
    kept = hard_filter(deals(), p, TODAY)
    detergents = [d for d in kept if d.product_type == "detergent"]
    assert detergents and all(d.brand == "Tide" for d in detergents)


def test_weekly_limit_respected():
    picks = match(deals(), profile(avoid=[], max_deals_per_week=3), retriever="tfidf", use_llm=False, today=TODAY)
    assert len(picks) <= 3


def test_flagged_links_are_dropped():
    good = Deal("A", "S", TODAY, TODAY, url="https://ok.example", link_safe=True)
    bad = Deal("B", "S", TODAY, TODAY, url="https://bad.example", link_safe=False)
    unchecked = Deal("C", "S", TODAY, TODAY, url="https://new.example")
    kept = hard_filter([good, bad, unchecked], UserProfile(name="x"), TODAY)
    assert {d.title for d in kept} == {"A", "C"}


def test_demo_profiles_get_different_deals():
    import glob

    results = {}
    for path in sorted(glob.glob("profiles/*.json")):
        p = UserProfile.load(path)
        results[path] = {d.deal_id for d in match(deals(), p, retriever="tfidf", use_llm=False, today=TODAY)}
    a, b = results["profiles/eats_out.json"], results["profiles/grocery_saver.json"]
    assert a and b and not (a & b)
