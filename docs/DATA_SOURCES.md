# Data sources

## Decision from the meeting

Near the end of the meeting the team decided to **"scratch everything we said about web scraping"** as the main approach and use:

1. **Deal APIs / RSS feeds** for national and online deals. Crowd-sourced deal sites already do the finding and vetting, so we rely on that collective work instead of searching from scratch.
2. **Agentic web search** for **local** deals (Provo / Utah County), limited by the user's location and radius.
3. Optionally, **public** community sources (Facebook groups, local deal pages), and later an agent-owned inbox subscribed to store promo emails (Tier 2).

Why: most organizations treat scraping as using their computing resources even when the pages are public. Scrapers break whenever HTML changes, and the instructor pointed out that relying on feeds is safer and more defensible.

## Sources

| Source | Covers | Method | Status |
|---|---|---|---|
| Slickdeals Frontpage RSS | National, online, Amazon-heavy (also household items, not only electronics) | RSS: `https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1` | 🟡 `sources/slickdeals.py` |
| Slickdeals Popular / Coupons / Freebies RSS | Same, broader | Same URL pattern, other `mode` / `forumchoice` values | add to `FEEDS` list |
| Local web search (agent) | Provo/Orem restaurants, local shops, oil changes | LLM with a web-search tool: "deals this week near {location} for {category}" → structured `Deal` JSON | ⬜ `sources/local_search.py` stub |
| Hand-entered / mailers | Anything a teammate finds (e.g., a Cafe Rio mailer) | Add to `data/sample_deals.json` | ✅ |
| Paper coupon photo | Mailers | Vision model → `Deal` | Tier 3 |
| Agent-owned inbox | Store promo emails | Gmail API on a project-only address | Tier 2 |

Caveats:
- Users have reported the Slickdeals feeds pausing at times. Run the snapshot early, and keep `sample_deals.json` as the backup for the demo.
- Slickdeals publishes these feeds for RSS readers, but its `robots.txt` disallows automated fetching of the `newsearch.php` path (an automated fetch tool refused it on those grounds). Reading the feed once a week like an RSS reader is the intended use; still, **confirm this with the professor** and note it in the presentation. If he says no, switch to a feed or API whose terms clearly allow it.
- The parser was tested on a sample RSS file but not yet on the live feed (the dev container has no network access to it). Run `python -m calendeal.sources.slickdeals` on your machine first.
- **`data/sample_deals.json` is made up** (illustrative stores and codes for tests and wiring). Don't present it as real deals. The demo should use a real snapshot.

## Snapshot workflow (the "mega scrape")

```bash
python -m calendeal.main snapshot            # runs every source, saves data/snapshots/<date>.json
python -m calendeal.main snapshot --check-links   # also runs VirusTotal on each link (slow: 4/min)
python -m calendeal.main match --profile profiles/eats_out.json --snapshot latest --ics out/eats_out.ics
```

For the demo, take **one snapshot of a single week**, run link checks once (overnight is fine, which is how the meeting planned it), commit the snapshot, and run every profile against that same snapshot. The results stay reproducible and we stay inside the free API limits.

## Rules for adding a source

- Prefer an official API or RSS over HTML scraping. If you do have to scrape, check `robots.txt` and the site's terms, send a clear User-Agent, cache results, and don't hit the site more than once per run.
- Only use public pages. Don't log in as a user to collect deals.
- Map everything into `Deal`. Fill `promo_code`, `url`, `end`, and `category` whenever the source has them, because the matcher and calendar depend on them.
- One broken source must not break the run. `fetch_all()` already catches errors per source.
