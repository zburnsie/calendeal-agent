"""Write picked deals to an .ics calendar that Apple Calendar, Google Calendar, and Outlook all accept.

- Import the file once, or host it at a URL and *subscribe*: when we regenerate the file
  (new week, or a deal the user swiped away), every subscribed calendar updates.
- All-day events across the deal window, a reminder before start, the promo code and link in the notes.
- UID = deal_id, so re-imports update events instead of duplicating them.

No extra dependency: the format is simple enough to write by hand (RFC 5545).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from calendeal.models import Deal

PRODID = "-//CalenDeal Agent//EN"


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Lines longer than 75 octets must be folded (CRLF + space)."""
    out, cur = [], b""
    for ch in line:
        b = ch.encode()
        if len(cur) + len(b) > 75:
            out.append(cur.decode())
            cur = b" "
        cur += b
    out.append(cur.decode())
    return "\r\n".join(out)


def describe(deal: Deal) -> str:
    """Event notes. Shared with gcal.py so both calendars say the same thing."""
    lines = [f"{deal.store} · {deal.channel}"]
    if deal.reason:
        lines.append(f"Why you: {deal.reason}")
    if deal.promo_code:
        lines.append(f"Promo code: {deal.promo_code}")
    if deal.description:
        lines.append(deal.description)
    if deal.url:
        lines.append(deal.url)
    if deal.link_safe is None and deal.url:
        lines.append("(link not yet safety-checked)")
    lines.append(f"Ends {deal.end:%a %b %d}")
    return "\n".join(lines)


def to_vevent(deal: Deal, reminder_minutes: int, stamp: str) -> list[str]:
    summary = f"{deal.title} · {deal.store}"
    if deal.promo_code:
        summary += f" · code {deal.promo_code}"
    lines = [
        "BEGIN:VEVENT",
        f"UID:{deal.deal_id}@calendeal",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{deal.start:%Y%m%d}",
        f"DTEND;VALUE=DATE:{deal.end + timedelta(days=1):%Y%m%d}",  # all-day end is exclusive
        f"SUMMARY:{_esc(summary)}",
        f"DESCRIPTION:{_esc(describe(deal))}",
        "TRANSP:TRANSPARENT",  # don't block free/busy
        f"CATEGORIES:{_esc(deal.category or 'deal')}",
    ]
    if deal.location:
        lines.append(f"LOCATION:{_esc(deal.location)}")
    if deal.url:
        lines.append(f"URL:{deal.url}")
    lines += [
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_esc(summary)}",
        f"TRIGGER:-PT{reminder_minutes}M",
        "END:VALARM",
        "END:VEVENT",
    ]
    return lines


def build_ics(deals: list[Deal], calendar_name: str | None = None) -> str:
    name = calendar_name or os.getenv("CALENDEAL_CALENDAR_NAME", "CalenDeal Agent")
    tz = os.getenv("CALENDEAL_TIMEZONE", "America/Denver")
    minutes = int(os.getenv("CALENDEAL_REMINDER_MINUTES", "720"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_esc(name)}",
        f"X-WR-TIMEZONE:{tz}",
        "X-WR-CALDESC:Deals picked for you by the CalenDeal Agent. Hide this calendar to hide all deals.",
    ]
    for d in deals:
        lines += to_vevent(d, minutes, stamp)
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"


def write_ics(deals: list[Deal], path: str | Path, calendar_name: str | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_ics(deals, calendar_name), encoding="utf-8", newline="")
    return path
