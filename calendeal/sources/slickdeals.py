"""National / online deals from Slickdeals' public RSS feeds (crowd-sourced, already vetted by the community).

RSS gives no expiry date, so a deal is assumed to run DEFAULT_DAYS from when it was posted (assumed).
Store, promo code, and category are pulled out of the title/description with simple rules;
improve the rules (or ask the LLM to structure them) if results look messy.

Not yet run against the live feed from the dev container (network blocked there). Run
`python -m calendeal.sources.slickdeals` on your machine and check the output.
See docs/DATA_SOURCES.md for usage rules.
"""
from __future__ import annotations

import html
import os
import re
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from email.utils import parsedate_to_datetime

from calendeal.models import Deal

FEEDS = [
    "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1",
    # "https://slickdeals.net/newsearch.php?mode=popdeals&searcharea=deals&searchin=first&rss=1",
    # coupons forum: "https://slickdeals.net/newsearch.php?searchin=first&forumchoice%5B%5D=10&rss=1",
]
DEFAULT_DAYS = int(os.getenv("CALENDEAL_RSS_DEAL_DAYS", "7"))
UA = {"User-Agent": "CalenDeal class project (BYU) - RSS reader"}

CATEGORY_WORDS = {
    "electronics": ["tv", "laptop", "headphone", "earbuds", "monitor", "ssd", "iphone", "ipad", "camera", "speaker", "gaming", "switch", "xbox", "ps5", "charger"],
    "grocery": ["detergent", "toilet paper", "paper towel", "coffee pods", "snack", "cereal", "toothpaste", "shampoo", "diapers", "grocery"],
    "clothing": ["shirt", "jacket", "shoes", "sneakers", "hoodie", "jeans", "socks", "apparel", "pajama"],
    "home": ["vacuum", "mattress", "sheets", "cookware", "skillet", "furniture", "air fryer", "kitchen", "tool"],
    "health & beauty": ["vitamin", "razor", "skincare", "makeup", "toothbrush"],
    "entertainment": ["movie", "tickets", "game pass", "streaming", "subscription"],
    "car": ["tire", "oil change", "motor oil", "car wash", "wiper"],
    "food": ["pizza", "burger", "restaurant", "doordash", "free food", "sandwich"],
}
STORE_RE = re.compile(r"(?:\bat\b|@)\s+([A-Z][\w&'.\- ]{1,30}?)(?:\s*(?:\+|\(|$|,| w/| with| for))")
CODE_RE = re.compile(r"\b(?:code|coupon)[:\s]+\"?([A-Z0-9]{4,20})\b")
TAG_RE = re.compile(r"<[^>]+>")


def guess_category(text: str) -> str:
    t = text.lower()
    for cat, words in CATEGORY_WORDS.items():
        if any(re.search(rf"\b{re.escape(w)}(?:s|es)?\b", t) for w in words):
            return cat
    return "shopping"


def parse_item(item: ET.Element) -> Deal | None:
    title = html.unescape((item.findtext("title") or "").strip())
    if not title:
        return None
    link = (item.findtext("link") or "").strip()
    raw_desc = item.findtext("description") or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or ""
    desc = re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw_desc))).strip()[:400]
    try:
        posted = parsedate_to_datetime(item.findtext("pubDate") or "").date()
    except (TypeError, ValueError):
        posted = date.today()

    m = STORE_RE.search(title + " ")
    store = m.group(1).strip() if m else "Online"
    code = CODE_RE.search(f"{title} {desc}")
    return Deal(
        title=title[:120],
        store=store,
        start=posted,
        end=posted + timedelta(days=DEFAULT_DAYS),
        description=desc,
        category=guess_category(f"{title} {desc}"),
        channel="online",
        url=link,
        promo_code=code.group(1) if code else "",
        source="slickdeals",
    )


def parse_feed(xml_text: str) -> list[Deal]:
    root = ET.fromstring(xml_text)
    deals = [parse_item(it) for it in root.iter("item")]
    return [d for d in deals if d]


def fetch() -> list[Deal]:
    import requests

    deals: list[Deal] = []
    for url in FEEDS:
        r = requests.get(url, headers=UA, timeout=20)
        r.raise_for_status()
        deals.extend(parse_feed(r.text))
    return deals


if __name__ == "__main__":
    for d in fetch()[:15]:
        print(f"{d.start}  [{d.category}] {d.title} @ {d.store}  code={d.promo_code or '-'}")
