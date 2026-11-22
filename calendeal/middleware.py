"""Guardrails that run between ingest and matching. See docs/GUARDRAILS.md.

1. filter_invalid / filter_expired — cheap local checks, every run.
2. check_links — VirusTotal URL reputation. The free public API allows 4 requests/minute
   and 500/day, so run it ONCE per weekly snapshot (python -m calendeal.main snapshot --check-links).
   Results are cached in data/link_cache.json so a URL is never looked up twice.
"""
from __future__ import annotations

import base64
import json
import os
import time
from datetime import date
from pathlib import Path

from calendeal.models import Deal

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "link_cache.json"
VT_URL = "https://www.virustotal.com/api/v3/urls/{id}"
VT_SUBMIT = "https://www.virustotal.com/api/v3/urls"
PER_MINUTE = 4
DAILY_CAP = 500


def filter_invalid(deals: list[Deal]) -> list[Deal]:
    return [d for d in deals if d.title.strip() and d.store.strip()]


def filter_expired(deals: list[Deal], today: date | None = None) -> list[Deal]:
    return [d for d in deals if not d.is_expired(today)]


def filter_unsafe(deals: list[Deal]) -> list[Deal]:
    """Drop deals whose link was flagged. Unchecked (None) links are kept; the UI shows them as unverified."""
    return [d for d in deals if d.link_safe is not False]


def _load_cache() -> dict[str, bool]:
    try:
        return json.loads(CACHE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict[str, bool]) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True))


def _vt_lookup(url: str, key: str) -> bool | None:
    """True = clean, False = flagged, None = unknown (not in VT yet / error)."""
    import requests

    url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
    r = requests.get(VT_URL.format(id=url_id), headers={"x-apikey": key}, timeout=20)
    if r.status_code == 404:
        # Not seen before: submit it so a later run has a verdict. Counts as a request.
        requests.post(VT_SUBMIT, headers={"x-apikey": key}, data={"url": url}, timeout=20)
        return None
    if r.status_code == 429:
        raise RuntimeError("VirusTotal quota hit")
    r.raise_for_status()
    stats = r.json()["data"]["attributes"]["last_analysis_stats"]
    return (stats.get("malicious", 0) + stats.get("suspicious", 0)) == 0


def check_links(deals: list[Deal], key: str | None = None, sleep=time.sleep) -> list[Deal]:
    """Set deal.link_safe for every deal with a URL. Throttled to the free tier; uses and updates the cache."""
    key = key or os.getenv("VIRUSTOTAL_API_KEY")
    cache = _load_cache()
    for d in deals:
        if d.url in cache:
            d.link_safe = cache[d.url]
    todo = sorted({d.url for d in deals if d.url and d.url not in cache})
    if not todo:
        return deals
    if not key:
        print(f"[warn] VIRUSTOTAL_API_KEY not set; {len(todo)} link(s) left unverified")
        return deals

    print(f"Checking {len(todo)} link(s) with VirusTotal (~{len(todo) * 60 // PER_MINUTE // 60 + 1} min)...")
    results: dict[str, bool | None] = {}
    for n, url in enumerate(todo[:DAILY_CAP]):
        if n and n % PER_MINUTE == 0:
            sleep(61)
        try:
            results[url] = _vt_lookup(url, key)
        except RuntimeError as e:
            print(f"[warn] {e}; stopping link checks for today")
            break
        except Exception as e:  # network hiccup on one URL shouldn't kill the batch
            print(f"[warn] VirusTotal failed for {url}: {e}")
        if results.get(url) is not None:
            cache[url] = results[url]
    _save_cache(cache)

    for d in deals:
        if d.url in cache:
            d.link_safe = cache[d.url]
    flagged = sum(1 for v in cache.values() if v is False)
    print(f"Link check done: {len(cache)} cached verdict(s), {flagged} flagged")
    return deals


def clean(deals: list[Deal], today: date | None = None) -> list[Deal]:
    """The checks that run on every match: invalid, expired, flagged links (from cache)."""
    deals = filter_expired(filter_invalid(deals), today)
    cache = _load_cache()
    for d in deals:
        if d.link_safe is None and d.url in cache:
            d.link_safe = cache[d.url]
    return filter_unsafe(deals)
