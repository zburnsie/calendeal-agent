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
