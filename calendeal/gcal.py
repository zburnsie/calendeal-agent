"""Optional: write matched deals straight to Google Calendar through its API.

The default output is an .ics file (calendeal/ics.py), which works with Apple and Google.
Use this path if you want events pushed into Google directly.

- Everything goes on one calendar ("CalenDeal Agent"), so the user can hide all deals with one toggle.
- Deals are all-day events spanning start..end, with a popup reminder before they start.
- Each event stores the deal_id in extendedProperties so re-running never duplicates.
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from calendeal.ics import describe
from calendeal.models import Deal

SCOPES = ["https://www.googleapis.com/auth/calendar"]
ROOT = Path(__file__).resolve().parents[1]
CREDS = ROOT / "credentials.json"
TOKEN = ROOT / "token.json"


def service():
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS.exists():
                raise SystemExit("Missing credentials.json — see README 'Google Calendar setup'.")
            creds = InstalledAppFlow.from_client_secrets_file(str(CREDS), SCOPES).run_local_server(port=0)
        TOKEN.write_text(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def get_or_create_calendar(svc, name: str | None = None) -> str:
    name = name or os.getenv("CALENDEAL_CALENDAR_NAME", "CalenDeal Agent")
    page = None
    while True:
        resp = svc.calendarList().list(pageToken=page).execute()
        for cal in resp.get("items", []):
            if cal.get("summary") == name:
                return cal["id"]
        page = resp.get("nextPageToken")
        if not page:
            break
    cal = svc.calendars().insert(body={
        "summary": name,
        "timeZone": os.getenv("CALENDEAL_TIMEZONE", "America/Denver"),
        "description": "Deals picked for you by the CalenDeal Agent. Hide this calendar to hide all deals.",
    }).execute()
    return cal["id"]


def existing_deal_ids(svc, cal_id: str) -> set[str]:
    ids, page = set(), None
    while True:
        resp = svc.events().list(calendarId=cal_id, pageToken=page, maxResults=250).execute()
        for ev in resp.get("items", []):
            did = ev.get("extendedProperties", {}).get("private", {}).get("deal_id")
            if did:
                ids.add(did)
        page = resp.get("nextPageToken")
        if not page:
            return ids


def to_event(deal: Deal) -> dict:
    minutes = int(os.getenv("CALENDEAL_REMINDER_MINUTES", "720"))
    summary = f"{deal.title} · {deal.store}"
    if deal.promo_code:
        summary += f" · code {deal.promo_code}"
    return {
        "summary": summary,
        "description": describe(deal),
        "location": deal.location,
        "start": {"date": deal.start.isoformat()},
        "end": {"date": (deal.end + timedelta(days=1)).isoformat()},  # all-day end is exclusive
        "transparency": "transparent",  # don't block the user's free/busy time
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": minutes}]},
        "extendedProperties": {"private": {"deal_id": deal.deal_id, "source": deal.source}},
    }


def add_deals(deals: list[Deal]) -> int:
    svc = service()
    cal_id = get_or_create_calendar(svc)
    seen = existing_deal_ids(svc, cal_id)
    added = 0
    for d in deals:
        if d.deal_id in seen:
            continue
        svc.events().insert(calendarId=cal_id, body=to_event(d)).execute()
        added += 1
    return added
