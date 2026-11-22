# Handoff log

Newest entry at the top. Every work session (you + your Claude) adds one before stopping.

Template:

```
## YYYY-MM-DD — <name> (+ Claude) — branch <branch>
**Did:**
**Left / next:**
**Broken or unsure:**
**Files touched:**
```

---

## 2026-11-21 — Olivia (+ Claude) — branch `claude/v1`

**Did:** First local run on a real machine: venv (Python 3.11), `pip install -r requirements.txt`, `.env` from the template. `pytest` passes (35), `try_profiles.py --retriever embed` passes every check, the live Slickdeals feed parses (25 deals), `snapshot` works (59 deals), and the Gradio app loads with no key. Confirmed offline that `deepseek-flash` is a valid DeepSeek id and that thinking is sent as disabled. Results and the Slickdeals problems are in `docs/EVALUATION.md` → "Live run log".

**Left / next:**
1. Put `DEEPSEEK_API_KEY` in `.env`, then run `python scripts/try_profiles.py --llm` (and `--llm --retriever embed`), then `python -m app.app` and the chat examples, including Approve **and** Reject in "Ask me first" mode. This is still the first real test of DeepSeek tool calling.
2. `CALENDEAL_LOCAL_SEARCH=1 python -m calendeal.main snapshot`: look at the local deals before tuning `QUERIES`.
3. Slickdeals fixes: take the store from the merchant link in the description; fix the category keywords (see the Live run log).
4. Leave the made-up `sample` deals out of the real demo snapshot, then take it with `--check-links`.
5. **Deal sources: no web scraping** (D7 replaced it). What we have: one Slickdeals RSS feed (works live, national/online only, robots.txt question still open with the professor) and `local_search.py` (DuckDuckGo snippets + LLM, never run live). Next person:
   - Run local search live (step 2) and judge whether it finds real Provo deals with dates and codes.
   - Find 1–2 real deal **APIs or feeds whose terms allow this use**, especially local and student deals, and add each as a `sources/<name>.py` with `fetch()` (see `DATA_SOURCES.md` → "Rules for adding a source").
   - Turn on the other Slickdeals feeds (Popular, Coupons, Freebies in `FEEDS`) once the professor says the feed is OK.
   - Make `radius_miles` actually filter local deals.

**Broken or unsure:**
- Nothing has hit the DeepSeek API yet.
- `data/snapshots/2026-11-21.json` was not committed on purpose: it mixes in the made-up samples and links weren't checked.
- Python 3.14 is too new for torch/chromadb wheels. Use 3.11 or 3.12 for the venv.

**Files touched:** `docs/EVALUATION.md`, `docs/HANDOFF.md`, `app/app.py` (Inter font, tabs fit on one row at phone width).

---

## 2026-11-21 — Claude (matching check) — branch `claude/v1`

**Did:** Added `scripts/try_profiles.py`: three very different test users (Foodie Fran: food/entertainment, avoids alcohol; Household Hank: grocery/car/home, Tide + Colgate only; Gamer Gwen: electronics/gifts, online). It prints each user's weekly picks and the top results for 3 example chat questions, then runs PASS/FAIL checks. Added 14 more made-up sample deals (34 total), including traps the matcher must skip: a beer deal, other detergent/toothpaste brands, a flagged link, and an expired deal. All checks pass with TF-IDF; the 3 users share 0% of their picks. 35 tests.

**Left / next:** Run it with `--retriever embed` and `--llm` on a machine with the models/key, and on the real snapshot (`--snapshot latest`). Record the numbers in `docs/EVALUATION.md`.

**Broken or unsure:** `radius_miles` / `location` are saved but not used to filter deals yet (everything in the sample is Provo/Orem). Worth adding once real local deals come in.

**Files touched:** `scripts/try_profiles.py` (new), `tests/test_try_profiles.py` (new), `data/sample_deals.json`, `docs/EVALUATION.md`, `README.md`.

---

## 2026-11-21 — Claude (v1 build) — branch `claude/v1`

**Did:**
- **LLM = DeepSeek** (`calendeal/llm.py`): `deepseek-flash` through LangChain `init_chat_model`, thinking mode off (DeepSeek requires passing reasoning back once tools are used, which the agent loop doesn't do). Swap with `CALENDEAL_LLM`. `structured()` = Pydantic + bounded retry, like the Lab 4 script. The matcher's rerank now uses it.
- **Local deal search** (`sources/local_search.py`): DuckDuckGo via `ddgs` (free) → LLM pulls deals out of the snippets → a deal is kept only if its URL was one of the search results.
- **Chat agent** (`calendeal/agent.py`): `create_agent` with tools `search_deals`, `weekly_picks`, `find_local_deals`, `add_to_calendar`, `remove_from_calendar`, `my_calendar`. In approve mode, `HumanInTheLoopMiddleware` pauses `add_to_calendar` until the user taps Approve. Works with no key too (falls back to plain search).
- **Per-user store** (`calendeal/store.py`): profile, calendar, dismissed deals; the `.ics` is rebuilt on every change, so removing a deal removes it from the calendar.
- **Web app** (`app/app.py`, Gradio, phone-width): Start (Pinterest-style intake) → This week ("what we learned about you" + picks to approve) → Calendar (download `.ics`, remove deals) → Chat (with Approve/Reject when the agent wants to add).
- `docs/LAB_PATTERNS.md` maps each lab to where its pattern is used.
- Tests: 33 passing (agent with a scripted fake model including approve/reject, store, local search, rerank). Clicked through the app in headless Chrome at phone size.

**Left / next:**
1. **Run it live with a DeepSeek key** (I had no key and no network to DeepSeek): put `DEEPSEEK_API_KEY` in `.env`, run `python -m app.app`, try the chat examples. Watch for tool-call problems; if the agent loops or errors, try `CALENDEAL_LLM=anthropic:claude-haiku-4-5` to see whether it's DeepSeek-specific.
2. Live-test `CALENDEAL_LOCAL_SEARCH=1 python -m calendeal.main snapshot` and look at what the local deals look like. Tune `QUERIES` in `local_search.py`.
3. Take the real demo snapshot (`snapshot --check-links`), commit it, and run `docs/EVALUATION.md`.
4. UI polish: per-card toggles in chat, swipe to dismiss, a hosted `.ics` subscribe URL.

**Broken or unsure:**
- Nothing has run against the real DeepSeek API, Slickdeals, or DuckDuckGo yet (no network from the build machine). The code paths are tested with fakes.
- The demo picks still come from the made-up `sample_deals.json` until someone takes a real snapshot.
- Gradio state is in memory: restarting the app clears chat (profiles and calendars are saved on disk under `data/users/`, which is git-ignored).

**Files touched:** `calendeal/llm.py` (new), `calendeal/agent.py` (new), `calendeal/store.py` (new), `calendeal/sources/local_search.py`, `calendeal/matcher.py`, `calendeal/models.py`, `app/` (new), `tests/` (fakes + 3 new files), `docs/*`, `README.md`, `CLAUDE.md`, `.env.example`, `requirements.txt`, `.gitignore`.

---

## 2026-11-21 — Claude, from the kickoff transcript — branch `kickoff-plan-and-fixes`

**Did:**
- Turned the kickoff meeting into planning docs: `docs/PRODUCT_SPEC.md`, `PRIORITIES.md` (tiers), `ARCHITECTURE.md`, `DATA_SOURCES.md`, `GUARDRAILS.md`, `EVALUATION.md`, `TEAM_WORKFLOW.md`, `DECISIONS.md`, plus `CLAUDE.md` at the root for every teammate's Claude.
- Brought the code in line with the meeting decisions:
  - `models.py`: added `promo_code`, `brand`, `product_type`, `link_safe` to `Deal`; added `categories` (intake checkboxes), `brand_loyal`, `notes`, `radius_miles`, `hitl_mode` (auto/approve), and a 20/week cap to `UserProfile`.
  - **New `ics.py`**: `.ics` calendar output for Apple and Google, now the default instead of Google-only. Events include the promo code, link, "why you" line, and a reminder.
  - **New `middleware.py`**: drops expired/invalid deals; VirusTotal link check throttled to 4/min with a cache, run once per snapshot.
  - **New `snapshot.py`** + `main.py snapshot`: the weekly "mega scrape" saved to `data/snapshots/`.
  - **New `sources/slickdeals.py`**: RSS source (replaces the scraping plan). `sources/local_search.py` is a documented stub for agent web search of local deals.
  - `matcher.py`: hard filters (categories, avoid, brand loyalty, expired, unsafe links) → Chroma + all-MiniLM-L6-v2 semantic search (TF-IDF fallback) → boosts → Claude rerank.
  - `main.py`: `snapshot` / `match` commands, `--ics` (default), `--gcal`, `--retriever`, `--no-llm`, `--today`, approve-mode prompt.
  - 3 demo profiles (`eats_out`, `grocery_saver`, `online_shopper`) that get completely different picks; 20 sample deals.
  - Tests: 21 passing (ICS validity, middleware throttle/cache, RSS parsing, brand loyalty, profile separation…).

**Left / next (in order):**
1. Run `python -m calendeal.sources.slickdeals` on a real machine. The parser hasn't seen the live feed yet. Fix the store/category rules if they're off.
2. Build `sources/local_search.py` (Tier 1.3). The plan is in its docstring.
3. Build `calendeal/agent.py`, the RAG chat agent (Tier 1.7), from the Lab 2 chatbot + the middleware/HITL lab.
4. Gradio web app in `app/` (Tier 1.9–1.10): intake checkboxes → profile, deal cards, `.ics` download, chat.
5. Take the real one-week snapshot with `--check-links`, commit it, and run the evaluation (`docs/EVALUATION.md`).

**Broken or unsure:**
- Embedding retrieval (`--retriever embed`) is written but untested here because the model download was blocked. Run `pytest` and a `--retriever embed` match locally once `chromadb` and `sentence-transformers` are installed.
- Slickdeals' robots.txt disallows automated fetching of the feed path. Ask the professor (see `DATA_SOURCES.md`).
- Market stats in `PRODUCT_SPEC.md` need real sources.
- `data/sample_deals.json` is made up.

**Files touched:** everything under `calendeal/`, `docs/`, `profiles/`, `tests/`, plus `CLAUDE.md`, `README.md`, `.env.example`, `requirements.txt`, `.gitignore`.
