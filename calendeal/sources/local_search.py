"""Local deals (Provo / Utah County by default) found with web search + the LLM. Tier 1.3.

How it works:
  1. For each category, run a web search like "pizza deals this week Provo UT" (DuckDuckGo via the
     free `ddgs` package, so no search API key is needed).
  2. Hand ONLY the search snippets (title, link, summary) to the LLM and ask for structured deals
     (Pydantic schema + bounded retry, same as the Lab 4 structured-output script).
  3. Keep a deal only if its URL is one of the search results: the model can't invent a source.

We read search-result snippets, not the sites themselves, so this isn't scraping. Every URL still
goes through middleware.py (VirusTotal) before it can reach a calendar.

Off unless CALENDEAL_LOCAL_SEARCH=1, because each run costs a few LLM calls.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

from pydantic import BaseModel, Field

from calendeal import llm
from calendeal.models import CATEGORIES, Deal

LOCATION = os.getenv("CALENDEAL_LOCATION", "Provo, UT")
RESULTS_PER_QUERY = 8

# What to search for in each intake category (local, in-person things first).
QUERIES = {
    "food": ["restaurant deals this week", "BOGO food deal", "student discount food"],
    "grocery": ["grocery store weekly ad deals"],
    "car": ["oil change coupon", "car wash deal"],
    "entertainment": ["discount movie tickets", "student discount activities"],
    "clothing": ["clothing store sale this week"],
    "health & beauty": ["haircut deal", "pharmacy weekly deals"],
}


class FoundDeal(BaseModel):
    title: str = Field(description="short name of the deal, e.g. 'BOGO burritos'")
    store: str = Field(description="business name")
    url: str = Field(description="the search result link this deal came from, copied exactly")
    description: str = Field(default="", description="one sentence: what you get and any conditions")
    promo_code: str = Field(default="", description="code to use, if the snippet gives one")
    start: str | None = Field(default=None, description="YYYY-MM-DD if stated, else null")
    end: str | None = Field(default=None, description="YYYY-MM-DD if stated, else null")
    channel: str = Field(default="in store", description="'in store', 'online', or 'in store & online'")


class FoundDeals(BaseModel):
    deals: list[FoundDeal]


def web_search(query: str, max_results: int = RESULTS_PER_QUERY) -> list[dict]:
    from ddgs import DDGS

    return [
        {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
        for r in DDGS().text(query, max_results=max_results)
    ]


def _parse_date(s: str | None, fallback: date) -> date:
    try:
        return date.fromisoformat(s) if s else fallback
    except ValueError:
        return fallback


def extract(results: list[dict], category: str, location: str, today: date, model=None) -> list[Deal]:
    """Turn search snippets into Deals with the LLM. Drops anything whose URL wasn't in the results."""
    if not results:
        return []
    listing = "\n".join(f"- {r['title']} | {r['url']} | {r['snippet']}" for r in results)
    prompt = (
        f"Today is {today:%A %B %d, %Y}. These are web search results for {category} deals near {location}.\n"
        "List only real, specific deals at a named local business (a price, % off, BOGO, free item, "
        "or code). Skip listicles, news, coupon-aggregator homepages, and anything expired or not near "
        f"{location}. Copy the url exactly from the result it came from. "
        "Return an empty list if nothing qualifies.\n\n"
        f"Results:\n{listing}"
    )
    found = llm.structured(FoundDeals, prompt, model=model)
    if not found:
        return []

    allowed = {r["url"] for r in results}
    week_end = today + timedelta(days=6)
    deals = []
    for f in found.deals:
        if f.url not in allowed:
            continue  # guard: the model must cite one of the actual results
        start = _parse_date(f.start, today)
        end = max(_parse_date(f.end, week_end), start)
        deals.append(Deal(
            title=f.title[:120], store=f.store[:60], start=start, end=end,
            description=f.description[:300], category=category, channel=f.channel or "in store",
            url=f.url, location=location, promo_code=f.promo_code, source="local_search",
        ))
    return deals


def search(
    categories: list[str] | None = None,
    location: str = LOCATION,
    extra: str = "",
    today: date | None = None,
    model=None,
    searcher=web_search,
) -> list[Deal]:
    """Search for local deals. `extra` adds a targeted query ("look extra hard for X this week")."""
    today = today or date.today()
    model = model or llm.get_model(temperature=0)
    if model is None:
        print("[warn] local_search needs an LLM key (DEEPSEEK_API_KEY by default); skipped")
        return []

    plan: list[tuple[str, str]] = []
    for cat in categories or list(QUERIES):
        for q in QUERIES.get(cat, [f"{cat} deals"]):
            plan.append((cat, q))
    if extra:
        plan.insert(0, ("shopping" if not categories else categories[0], extra))

    deals: list[Deal] = []
    for cat, q in plan:
        try:
            results = searcher(f"{q} {location}")
        except Exception as e:
            print(f"[warn] search failed for '{q}': {e}")
            continue
        deals.extend(extract(results, cat if cat in CATEGORIES else "shopping", location, today, model))
    return deals


def fetch() -> list[Deal]:
    if os.getenv("CALENDEAL_LOCAL_SEARCH") != "1":
        return []
    return search()
