"""Reads hand-entered deals from data/sample_deals.json.

Use this as the template for real scrapers. A real one usually looks like:

    import requests
    from bs4 import BeautifulSoup

    def fetch():
        html = requests.get(URL, timeout=15, headers={"User-Agent": "CalenDeal class project"}).text
        soup = BeautifulSoup(html, "html.parser")
        return [Deal(title=..., store=..., start=..., end=...) for card in soup.select(".deal")]

Check each site's terms/robots.txt first; an RSS feed or public API is better than scraping when one exists.
"""
import json
from pathlib import Path

from calendeal.models import Deal

DATA = Path(__file__).resolve().parents[2] / "data" / "sample_deals.json"


def fetch() -> list[Deal]:
    return [Deal.from_dict(d) for d in json.loads(DATA.read_text())]
