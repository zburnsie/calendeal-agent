# Guardrails

What keeps the agent from doing something bad, and how each guardrail maps to what we covered in class (middleware, human-in-the-loop).

## 1. Link safety middleware — Tier 1

Every deal URL is checked with the **VirusTotal** public API before it can reach a user.

- Free limits: **4 requests/minute, 500/day**. The public API is for non-commercial / academic use, which fits a class project.
- So we check **once per weekly snapshot** (a batch job, overnight is fine), not on every request. Results are cached in `data/link_cache.json`, so a URL is never checked twice.
- Code: `calendeal/middleware.py` → `check_links()`. It throttles to 4/min and stops before the daily cap.
- A deal is dropped if any engine flags its URL as **malicious** or **suspicious**. If a URL hasn't been checked (no key, or the cap was hit), it is kept but marked `link_safe = None`, and the UI should show it as "unverified".
- Key: `VIRUSTOTAL_API_KEY` in `.env`. Without a key the step is skipped with a warning.

## 2. Expired and fake deals — Tier 1

- Drop any deal whose `end` date has passed (`filter_expired()`).
- Drop deals with no title or store.
- Optional rule: be wary of deals that look too good ("90%+ off electronics"). Could be an LLM check later.

## 3. Human in the loop — Tier 2

- `UserProfile.hitl_mode`:
  - `auto`: deals go straight onto the CalenDeal calendar.
  - `approve`: the agent proposes, and the user taps to approve or reject each one first.
- For the chat agent, wrap the `add_to_calendar` tool in LangChain's `HumanInTheLoopMiddleware` (same pattern as `middlewareHITLMAS.py` from the lab), with `allowed_decisions: approve / edit / reject`, when the user's mode is `approve`.
- The agent writes **only to its own CalenDeal calendar**, never to the user's main calendar. Turning that calendar off hides every deal, and removing it undoes everything. That keeps a wrong autonomous action cheap and reversible, which scores well on the matrix's "cost of autonomous error" row.

## 4. Limits

- `max_deals_per_week` caps calendar events (user-selectable, default 8, hard max 20).
- The agent never buys anything, never enters payment info, and never sends messages as the user.

## 5. Privacy

- Store only what the profile needs: interests, city or ZIP, and radius. No exact address, and no email unless the user turns on reminders.
- If the agent gets its own inbox to collect promo emails (Tier 2), use a **project-only email address**, never a user's real inbox.
- Never commit `.env`, `credentials.json`, or `token.json` (already in `.gitignore`).

## 6. Scraping ethics

See `docs/DATA_SOURCES.md`: APIs and RSS first, check `robots.txt`/terms before scraping anything, use public pages only, and cache results.
