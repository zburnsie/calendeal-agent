"""CalenDeal command line.

    # 1. weekly "mega scrape" -> data/snapshots/<date>.json  (add --check-links to run VirusTotal once)
    python -m calendeal.main snapshot [--sources sample slickdeals] [--check-links]

    # 2. match a profile and write a calendar
    python -m calendeal.main match --profile profiles/eats_out.json --snapshot latest --ics out/eats_out.ics
    python -m calendeal.main match --profile profiles/example.json --dry-run          # live sources, print only
    python -m calendeal.main match --profile profiles/example.json --gcal             # push to Google Calendar

Options for evaluation runs (docs/EVALUATION.md): --retriever tfidf|embed|auto, --no-llm, --today YYYY-MM-DD
"""
import argparse
from datetime import date

from dotenv import load_dotenv

from calendeal.models import UserProfile


def cmd_snapshot(args) -> None:
    from calendeal import snapshot
    from calendeal.middleware import check_links, filter_invalid
    from calendeal.sources import fetch_all

    print("Fetching from sources:")
    deals = filter_invalid(fetch_all(args.sources))
    if args.check_links:
        check_links(deals)
    path = snapshot.save(deals)
    print(f"Saved {len(deals)} deal(s) to {path}")


def cmd_match(args) -> None:
    from calendeal.matcher import match

    profile = UserProfile.load(args.profile)
    today = date.fromisoformat(args.today) if args.today else None

    if args.snapshot:
        from calendeal import snapshot
        deals = snapshot.load(args.snapshot)
        print(f"Loaded {len(deals)} deal(s) from snapshot {args.snapshot}")
    else:
        from calendeal.sources import fetch_all
        print("Fetching from sources:")
        deals = fetch_all(args.sources)

    picks = match(deals, profile, retriever=args.retriever, use_llm=not args.no_llm, today=today)
    print(f"\nPicked for {profile.name} ({profile.hitl_mode} mode, max {profile.max_deals_per_week}/week):")
    for d in picks:
        why = f" — {d.reason}" if d.reason else ""
        code = f" [code {d.promo_code}]" if d.promo_code else ""
        print(f"  {d.start:%a %b %d}  {d.title} @ {d.store}{code}  (score {d.score}){why}")

    if args.dry_run:
        print("\n--dry-run: no calendar written")
        return
    if profile.hitl_mode == "approve" and not args.yes:
        # CLI stand-in for the tap-to-approve cards the web app will have.
        keep = []
        for d in picks:
            if input(f"Add '{d.title} @ {d.store}'? [Y/n] ").strip().lower() in ("", "y", "yes"):
                keep.append(d)
        picks = keep

    if args.gcal:
        from calendeal.gcal import add_deals  # imported late so other paths don't need Google libs/auth
        n = add_deals(picks)
        print(f"\nAdded {n} new event(s) to the CalenDeal Google calendar")
    else:
        from calendeal.ics import write_ics
        out = args.ics or f"out/{profile.name.lower().replace(' ', '_')}.ics"
        path = write_ics(picks, out)
        print(f"\nWrote {len(picks)} event(s) to {path}. Import it into Apple or Google Calendar.")


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser(description="CalenDeal Agent")
    ap.add_argument("command", nargs="?", choices=["match", "snapshot"], default="match")
    ap.add_argument("--profile", default="profiles/example.json")
    ap.add_argument("--sources", nargs="*", help="limit to these sources (default: all)")
    ap.add_argument("--snapshot", help="match against a saved snapshot: 'latest', a date, or a path")
    ap.add_argument("--check-links", action="store_true", help="snapshot: run VirusTotal on every link (slow, 4/min)")
    ap.add_argument("--retriever", choices=["auto", "embed", "tfidf"], default="auto")
    ap.add_argument("--no-llm", action="store_true", help="skip the LLM rerank step")
    ap.add_argument("--today", help="pretend today is this date (YYYY-MM-DD), for demos on an old snapshot")
    ap.add_argument("--ics", help="where to write the .ics file (default out/<profile>.ics)")
    ap.add_argument("--gcal", action="store_true", help="write to Google Calendar via API instead of .ics")
    ap.add_argument("--yes", "-y", action="store_true", help="approve all picks (skip approve-mode prompts)")
    ap.add_argument("--dry-run", action="store_true", help="print matches, don't write any calendar")
    args = ap.parse_args()

    cmd_snapshot(args) if args.command == "snapshot" else cmd_match(args)


if __name__ == "__main__":
    main()
