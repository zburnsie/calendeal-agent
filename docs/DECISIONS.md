# Decision log

Decisions from the kickoff meeting (Nov 2026), plus anything decided later. Newest at the bottom. If you change a decision, add a new row; don't delete the old one.

| # | Decision | Why | Who / when |
|---|---|---|---|
| D1 | Product: an agent that finds deals that fit you and puts them on your calendar with reminders | Deals get missed or expire unused | Kickoff |
| D2 | Frame it as **saving on things you already buy**, not as encouraging spending | Real problem, honest value | Kickoff |
| D3 | v1 is a **web app with a mobile-first layout** (not a native app, not a Chrome extension) | Fastest to build; AI makes it easy to adapt to other platforms later | Kickoff |
| D4 | **Single agent**, not multi-agent | The professor said it doesn't matter; a debate setup isn't worth the complexity | Kickoff |
| D5 | Deals are stored as JSON → embedded → **semantic search / RAG** behind a chat agent with calendar tools | Reuses the Lab 1 and Lab 2 work | Kickoff |
| D6 | **Demo on one weekly snapshot** ("mega scrape") of Provo/Utah plus online deals, shown for 2–3 profiles | A strong demo doesn't need full coverage; it lets us focus on tailoring | Kickoff |
| D7 | **APIs / RSS feeds instead of web scraping** for national deals (Slickdeals first); **agent web search for local** deals by location/radius | Instructor raised the scraping-ethics concern; crowd-sourced feeds are already vetted | End of kickoff (overrides the earlier "manual scraping" plan) |
| D8 | Intake is **Pinterest-style category checkboxes + free-text notes/chat** | Checkboxes surface things people forget and become structured filters | Kickoff |
| D9 | Calendar output must work on **Apple and Google** → `.ics` feed/file | A teammate uses Apple Calendar | Kickoff |
| D10 | **HITL toggle**: auto-add vs. approve-first, with a **weekly cap** the user picks | Control and a clean calendar | Kickoff |
| D11 | **VirusTotal link checks in middleware**, run once per snapshot to stay in the free tier | Avoid scam and malicious links | Kickoff (Tier 1) |
| D12 | Tiered backlog: Tier 1 must / Tier 2 hope / Tier 3 nice | Avoid scope bloat | Kickoff |
| D13 | Work in turns, claim in the chat, leave a handoff `.md` after every session | Avoid merge conflicts; anyone can pick up the work | Kickoff |
| D14 | Everything lives in the GitHub repo, including class files | The last project's shared doc got messy | Kickoff |
| D15 | LLM = **DeepSeek `deepseek-flash`** through LangChain `init_chat_model`, thinking mode off; swappable with `CALENDEAL_LLM` | Team asked for a cheap API. Official price: $0.15–0.30 per 1M input, $0.60–1.20 per 1M output (off-peak/peak). Thinking mode needs reasoning_content passed back once tools are used, which breaks the agent loop | v1 build, Nov 21 |
| D16 | Web app in **Gradio** for v1 | Everyone used it in Lab 2; mobile layout via CSS | v1 build |
| D17 | Local search uses **DuckDuckGo via `ddgs`** (free, no key) + LLM extraction from snippets only; a deal is dropped unless its URL was in the search results | DeepSeek has no built-in web search; snippets aren't scraping; the URL rule blocks invented deals | v1 build |
| D18 | The app and agent work **without any API key** (retrieval order, search-only chat) | Demos never break on a missing key or quota | v1 build |

## Open questions

- Is reading the Slickdeals RSS feed once a week OK with the professor, given its robots.txt disallows automated fetching of that path? (See `DATA_SOURCES.md`.)
- Which local deal sources are actually reachable and allowed? (Facebook groups are mostly behind a login.)
- Gradio was chosen for v1 (D16). Revisit (e.g., React) only if the swipe-to-dismiss UI is a must.
- Host the `.ics` feed somewhere (so subscriptions auto-update) or just offer a download for the demo?
- ~~Which LLM?~~ DeepSeek (D15).
- Brand-loyal vs. "show me alternatives": default per category?

## Ideas we considered and set aside

| Idea | Status |
|---|---|
| Travel-deals agent | Other project idea, not chosen |
| Manual HTML scraping of many deal sites as the main source | Replaced by D7 (APIs/RSS + local agent search) |
| Multi-agent debate (e.g., a skeptic agent) | Not needed (D4); maybe Tier 3 for fun |
| Agent that only re-shows deals already on deal sites | Rejected: the value is tailoring plus finding local and less obvious deals |
| Native mobile app / Chrome extension for v1 | Deferred (D3) |
