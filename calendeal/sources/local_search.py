"""Local deals (Provo / Utah County) found by an LLM with web search. Tier 1, not built yet.

Plan (docs/DATA_SOURCES.md):
  for each category in CATEGORIES (or the categories any demo profile picked):
      ask Claude, with the web search tool turned on:
        "Find deals valid between {start} and {end} at businesses within {radius} miles of {location}
         for {category}. Only include deals with a source URL. Reply as JSON matching this schema: ..."
      validate each item into a Deal (Pydantic like script2PydanticStructured.py from the labs works well)
  return all deals

Notes:
- Ask for the source URL of every deal. The VirusTotal middleware checks those links.
- Plain "deals near me" web search tends to return the same generic top results; asking per category
  and per city works better.
- Disabled until CALENDEAL_LOCAL_SEARCH=1 so it doesn't spend API credits on every run.
"""
from __future__ import annotations

import os

from calendeal.models import Deal

LOCATION = os.getenv("CALENDEAL_LOCATION", "Provo, UT")


def fetch() -> list[Deal]:
    if os.getenv("CALENDEAL_LOCAL_SEARCH") != "1":
        return []
    raise NotImplementedError("local_search.fetch() is the next Tier 1 task. See the docstring for the plan.")
