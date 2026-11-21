# Priorities (tiered backlog)

The team agreed on a tiered list: **Tier 1 = must ship**, **Tier 2 = hope to ship**, **Tier 3 = cool if there's time**.
5 people × 3 weeks, with Claude doing a lot of the building, so the scope can be bigger than usual. Still, finish Tier 1 before you start Tier 2.

Status key: ✅ done · 🟡 started · ⬜ not started. Update it when you finish something.

## Tier 1 — must ship

| # | Item | Status | Notes |
|---|---|---|---|
| 1.1 | Problem statement written, with real cited stats | 🟡 | `docs/PRODUCT_SPEC.md`. Stats need sources. |
| 1.2 | Deal ingestion from **APIs / RSS** (Slickdeals feed first) | 🟡 | `calendeal/sources/slickdeals.py` |
| 1.3 | **Local deals for Provo/Utah** via agent web search, limited by location/radius | 🟡 | `sources/local_search.py` built + tested offline; needs a live run with a DeepSeek key |
| 1.4 | One-week **snapshot** ("mega scrape") saved to `data/snapshots/` | 🟡 | `python -m calendeal.main snapshot` |
| 1.5 | **Middleware**: drop expired deals + check every link with **VirusTotal**, run once per snapshot, within free API limits | 🟡 | `calendeal/middleware.py` |
| 1.6 | **Semantic search** over deals (embeddings + Chroma, like Lab 1), with a TF-IDF fallback | 🟡 | `calendeal/matcher.py`; embed path needs a local run |
| 1.7 | **RAG chat agent** (single agent) that answers from the deal store and can add to the calendar | 🟡 | `calendeal/agent.py`; tested with a scripted model, needs a live DeepSeek run |
| 1.8 | **Calendar output that works on Apple and Google**: `.ics` file / subscribable feed | ✅ | `ics.py` + per-user `store.py`; download in the app. Hosted subscribe URL = later |
| 1.9 | **Intake**: category checkboxes + free-text notes → `UserProfile` | ✅ | App "Start" tab |
| 1.10 | **Web app, mobile-friendly**: intake, deal list, calendar link, chat | ✅ v1 | `app/app.py` (Gradio). Polish welcome |
| 1.11 | **2–3 demo profiles** that get visibly different results | ✅ | `profiles/` |
| 1.12 | **Evaluation runs**: compare matcher settings 3–4 times and report the results | ⬜ | `docs/EVALUATION.md` |
| 1.13 | Weekly limit on deals per user | ✅ | `max_deals_per_week` |

## Tier 2 — hope to ship (the "agentic" layer)

| # | Item | Status | Notes |
|---|---|---|---|
| 2.1 | **Human-in-the-loop toggle**: auto-add vs. approve-first | ✅ | Picks tab (checkboxes) + chat (`HumanInTheLoopMiddleware`, Approve/Reject buttons) |
| 2.2 | **Tappable deal cards in chat** to approve/reject | 🟡 | Cards + Approve/Reject shown when the agent pauses; per-card toggles = later |
| 2.3 | **Promo code + direct link** in each calendar event | ✅ | In event title + notes |
| 2.4 | Remove a deal from the app → it disappears from the CalenDeal calendar (swipe to dismiss) | 🟡 | "Remove selected" on Calendar tab + chat tool; dismissed deals never return. Swipe gesture = later |
| 2.5 | "**Look extra hard for X this week**" → on-demand targeted search | 🟡 | Chat tool `find_local_deals` |
| 2.6 | **Brand-loyal vs. "any brand"** per product (Tide only vs. any detergent on sale) | ✅ | `brand_loyal` on the profile + intake field |
| 2.7 | "What we learned about you" editable profile page | ✅ | Top of "This week"; edit on Start |
| 2.8 | Agent gets its **own inbox** and signs up for store promo emails, then reads them as a source | ⬜ | Phase-2 idea from the meeting |
| 2.9 | Facebook group / community deal sources (public only) | ⬜ | Check terms first |

## Tier 3 — nice to have

| # | Item | Notes |
|---|---|---|
| 3.1 | **Photo of a paper coupon** (mailers like Cafe Rio) → read it with a vision model → add to calendar | |
| 3.2 | Text / email reminders | Calendar is the priority |
| 3.3 | Route planning to hit several deals in one trip | |
| 3.4 | AI promo-code autofill at checkout (like a password manager) | |
| 3.5 | Chrome extension / native mobile app | |
| 3.6 | Multi-agent debate (e.g., a skeptic agent that argues a deal is a scam) | The professor likes these, but the team chose a single agent |

## Explicitly out of scope

- Covering every site on the internet. A strong one-week demo is the goal.
- Buying anything or handling payments on the user's behalf.
- Broad scraping of sites that forbid it (see `docs/DATA_SOURCES.md`).
