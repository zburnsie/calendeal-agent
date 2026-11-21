"""Does the matching model actually work? Three very different test users, same deals, see what each gets.

    python scripts/try_profiles.py                     # sample deals, TF-IDF, no LLM (works offline)
    python scripts/try_profiles.py --llm               # + DeepSeek rerank with "why you" reasons
    python scripts/try_profiles.py --retriever embed   # Chroma + all-MiniLM-L6-v2 (Lab 1)
    python scripts/try_profiles.py --snapshot latest   # run on a real weekly snapshot instead

For each test user it prints:
  1. their weekly picks (what would go on their calendar)
  2. a few example questions they might ask the chat agent, and the top results for each

Then it runs automatic checks (PASS/FAIL) on the things the matcher must always get right:
categories, avoid list, brand loyalty, expired deals, flagged links, weekly limit, and that the
three users get mostly different deals. It exits with code 1 if any check fails, so you can use it
in the evaluation runs (docs/EVALUATION.md) after changing the retriever, prompt, or model.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

from calendeal import llm, matcher  # noqa: E402
from calendeal.models import Deal, UserProfile  # noqa: E402

# ---------- the three test users ----------

TEST_USERS = [
    {
        "profile": UserProfile(
            name="Foodie Fran",
            categories=["food", "entertainment"],
            interests=["tacos", "pizza", "coffee", "lattes", "date night", "movies"],
            avoid=["alcohol", "beer"],
            notes="Eats out with roommates, goes on cheap dates on weekends.",
            location="Provo, UT",
            max_deals_per_week=6,
        ),
        # (question, a word that should appear in a top-3 result)
        "questions": [("cheap tacos this week", "taco"), ("date night ideas", "date night"),
                      ("coffee deals", "coffee")],
    },
    {
        "profile": UserProfile(
            name="Household Hank",
            categories=["grocery", "health & beauty", "car", "home"],
            interests=["laundry detergent", "toothpaste", "paper towels", "oil change", "vacuum"],
            brand_loyal={"detergent": "Tide", "toothpaste": "Colgate"},
            notes="Married student, cooks at home, only buys Tide and Colgate.",
            location="Orem, UT",
            max_deals_per_week=8,
        ),
        "questions": [("detergent", "tide"), ("oil change", "oil change"), ("toothpaste", "colgate")],
    },
    {
        "profile": UserProfile(
            name="Gamer Gwen",
            categories=["electronics", "entertainment", "gifts", "shopping"],
            interests=["video games", "Nintendo Switch", "gaming headset", "board games", "gift for my brother"],
            prefers_online=True,
            notes="Christmas shopping for family; mostly buys online.",
            location="Provo, UT",
            max_deals_per_week=6,
        ),
        "questions": [("Nintendo Switch games", "switch"), ("headphones for gaming", "headset"),
                      ("gift for my brother", "gift")],
    },
]


# ---------- checks ----------

def check_picks(p: UserProfile, picks: list[Deal], today: date | None) -> list[tuple[str, bool, str]]:
    t = today or date.today()
    results = []

    def add(name, ok, detail=""):
        results.append((name, bool(ok), detail))

    add("gets at least 3 picks", len(picks) >= 3, f"{len(picks)} picks")
    add("respects weekly limit", len(picks) <= p.max_deals_per_week, f"limit {p.max_deals_per_week}")
    if p.categories:
        off = [d.title for d in picks if d.category and d.category not in p.categories]
        add("only their categories", not off, ", ".join(off))
    hits = [d.title for d in picks if any(a.lower() in d.text().lower() for a in p.avoid)]
    add("never shows avoid list", not hits, ", ".join(hits))
    wrong_brand = [d.title for d in picks
                   if d.product_type in p.brand_loyal and d.brand and d.brand != p.brand_loyal[d.product_type]]
    add("brand loyalty respected", not wrong_brand, ", ".join(wrong_brand))
    add("no expired deals", all(d.end >= t for d in picks))
    add("no flagged links", all(d.link_safe is not False for d in picks))
    return results


def overlap(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


# ---------- run ----------

def load_deals(snapshot: str | None) -> list[Deal]:
    if snapshot:
        from calendeal import snapshot as snap
        return snap.load(snapshot)
    from calendeal.sources import sample
    return sample.fetch()


def run(retriever: str = "tfidf", use_llm: bool = False, snapshot: str | None = None,
        today: date | None = None, quiet: bool = False) -> bool:
    say = (lambda *a, **k: None) if quiet else print
    deals = load_deals(snapshot)
    model = llm.get_model(temperature=0) if use_llm else None
    if use_llm and model is None:
        say("[note] --llm asked for, but no API key is set; running without the rerank.\n")
    say(f"{len(deals)} deals · retriever={retriever} · llm={'on: ' + llm.model_name() if model else 'off'}"
        f" · today={today or date.today()}\n")

    all_ok, pick_ids = True, {}
    for u in TEST_USERS:
        p = u["profile"]
        picks = matcher.match(list(deals), p, retriever=retriever, use_llm=model is not None,
                              today=today, model=model)
        pick_ids[p.name] = {d.deal_id for d in picks}

        say("=" * 70)
        say(f"{p.name}  ·  wants: {', '.join(p.categories)}  ·  likes: {', '.join(p.interests)}")
        if p.brand_loyal:
            say(f"  brand loyal: {p.brand_loyal}")
        if p.avoid:
            say(f"  avoid: {p.avoid}")
        say("-" * 70)
        say("Weekly picks:")
        for d in picks:
            why = f"  ← {d.reason}" if d.reason else ""
            say(f"  {d.score:>6.3f}  {d.title} @ {d.store} [{d.category}]{why}")

        say("\nExample questions:")
        for q, expect in u["questions"]:
            top = matcher.search(list(deals), p, q, k=3, retriever=retriever, today=today)
            ok = any(expect in d.text().lower() for d in top)
            all_ok &= ok
            say(f"  {'PASS' if ok else 'FAIL'}  \"{q}\" → " + (" | ".join(d.title for d in top) or "(nothing)"))

        say("\nChecks:")
        for name, ok, detail in check_picks(p, picks, today):
            all_ok &= ok
            say(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))
        say()

    say("=" * 70)
    say("Do different people get different deals?")
    names = list(pick_ids)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            o = overlap(pick_ids[names[i]], pick_ids[names[j]])
            ok = o <= 0.2
            all_ok &= ok
            say(f"  {'PASS' if ok else 'FAIL'}  {names[i]} vs {names[j]}: {o:.0%} overlap (want ≤ 20%)")

    say("\n" + ("ALL CHECKS PASSED ✅" if all_ok else "SOME CHECKS FAILED ❌"))
    return all_ok


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--retriever", choices=["tfidf", "embed", "auto"], default="tfidf")
    ap.add_argument("--llm", action="store_true", help="use the LLM rerank (needs DEEPSEEK_API_KEY)")
    ap.add_argument("--snapshot", help="'latest', a date, or a path; default = sample deals")
    ap.add_argument("--today", default=None,
                    help="pretend today is YYYY-MM-DD (default: 2026-11-22 for sample deals, real today for snapshots)")
    args = ap.parse_args()
    today = date.fromisoformat(args.today) if args.today else (None if args.snapshot else date(2026, 11, 22))
    sys.exit(0 if run(args.retriever, args.llm, args.snapshot, today) else 1)


if __name__ == "__main__":
    main()
