# Instructions for Claude (read this first)

You're helping one of 5 teammates build **CalenDeal**: an agent that finds deals a student would actually use and puts them on a CalenDeal calendar (Apple or Google) with reminders. It's a class project (agentic AI course). Teammates take turns working with their own Claude sessions, so leave the repo better documented than you found it.

## Before writing code

1. Read, in order:
   - `docs/HANDOFF.md` (top entry): where the last session stopped
   - `docs/PRIORITIES.md`: what to work on (finish Tier 1 before Tier 2)
   - `docs/PRODUCT_SPEC.md` and `docs/ARCHITECTURE.md`: what we're building and how it fits together
   - `docs/GUARDRAILS.md` and `docs/DATA_SOURCES.md` before touching sources, links, or the calendar
2. Ask your teammate which Tier item they're taking, and remind them to claim it in the group chat.
3. Work on a branch: `git checkout -b <name>/<thing>`.

## Rules

- **Single agent.** Don't add a multi-agent system without a decision in `docs/DECISIONS.md`.
- **No new scraping** of sites without checking terms/`robots.txt`. Prefer APIs/RSS (`docs/DATA_SOURCES.md`).
- **Every deal link goes through `calendeal/middleware.py`** before it can reach a calendar.
- The agent writes **only to its own CalenDeal calendar**, respects `hitl_mode` and `max_deals_per_week`, and never buys anything or sends messages as the user.
- Keep `Deal` / `UserProfile` in `calendeal/models.py` as the single shared data shape. Add fields with defaults so old snapshots still load.
- Reuse the lab patterns the team knows (Chroma + all-MiniLM-L6-v2, the LangChain `create_agent` + `HumanInTheLoopMiddleware`, Gradio) unless there's a reason not to.
- Never commit `.env`, `credentials.json`, or `token.json`.
- Tests must pass: `pytest`. Add a test for anything you add.

## Before the session ends

1. `pytest` passes.
2. Add a new entry at the **top** of `docs/HANDOFF.md` using the template there.
3. Update the status column in `docs/PRIORITIES.md`, and `docs/DECISIONS.md` if a decision changed.
4. Commit with a clear message, push the branch, open a PR, and remind your teammate to post in the group chat.
