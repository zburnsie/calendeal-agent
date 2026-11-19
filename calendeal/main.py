"""Run the whole agent: fetch deals -> match to a profile -> add to Google Calendar.

    python -m calendeal.main --profile profiles/example.json --dry-run
"""
import argparse

from dotenv import load_dotenv

from calendeal.matcher import match
from calendeal.models import UserProfile
from calendeal.sources import fetch_all


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser(description="CalenDeal Agent")
    ap.add_argument("--profile", default="profiles/example.json")
    ap.add_argument("--dry-run", action="store_true", help="print matches, don't touch the calendar")
    args = ap.parse_args()

    profile = UserProfile.load(args.profile)
    deals = fetch_all()
    print(f"Fetched {len(deals)} deals")

    picks = match(deals, profile)
    print(f"\nPicked for {profile.name}:")
    for d in picks:
        why = f" — {d.reason}" if d.reason else ""
        print(f"  {d.start:%a %b %d}  {d.title} @ {d.store}  (score {d.score}){why}")

    if args.dry_run:
        print("\n--dry-run: calendar not changed")
        return

    from calendeal.gcal import add_deals  # imported late so dry runs don't need Google libs/auth
    n = add_deals(picks)
    print(f"\nAdded {n} new event(s) to the CalenDeal calendar")


if __name__ == "__main__":
    main()
