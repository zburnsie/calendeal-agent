# Evaluation plan

The professor liked it in the labs when we ran a setup 3–4 times, changed one thing each time, and showed the results improve. Do the same here. One teammate should own this.

## What to measure

Use one fixed snapshot (`data/snapshots/<week>.json`) and the 3 demo profiles in `profiles/`.

1. **Relevance (precision@k).** For each profile, a teammate who didn't build the matcher labels the top 8 picks as relevant or not. Report the % relevant.
2. **Diversity.** How many categories and stores appear in each profile's picks? A calendar that's all one store is a bad calendar.
3. **Profile separation.** Overlap between profiles' picks (Jaccard). Different people should get mostly different deals.
4. **Safety.** Number of expired or flagged deals that reached a calendar. Target: 0.
5. **Reason quality** (with the LLM rerank). Is the "why you" line true and specific? Score each 1–3.

## Runs to compare (suggested)

| Run | Change | Why |
|---|---|---|
| 1 | TF-IDF retrieval only (baseline) | What the original scaffold did |
| 2 | Embeddings (all-MiniLM-L6-v2 + Chroma) | Semantic search from Lab 1 |
| 3 | Embeddings + category filter + store/brand boosts | Uses the intake checkboxes |
| 4 | Run 3 + LLM rerank with reasons (DeepSeek) | The full agent |

Keep the snapshot and profiles fixed across runs. Record results in a table in this file, with the date and the git commit for each run.

**Quick check first:** `python scripts/try_profiles.py` runs three very different test users (Foodie Fran, Household Hank, Gamer Gwen) against the same deals. It prints their picks and example chat searches, then PASS/FAIL checks on categories, avoid list, brand loyalty, expired deals, flagged links, the weekly limit, and overlap between users (≤ 20%). Add `--retriever embed`, `--llm`, or `--snapshot latest` to compare runs. Exit code 1 means something broke.

`python -m calendeal.main match --snapshot latest --profile profiles/X.json --retriever tfidf|embed --no-llm` switches between runs for one profile.

## Results

| Run | Date | Commit | Precision@8 (avg) | Categories (avg) | Overlap | Unsafe on calendar |
|---|---|---|---|---|---|---|
| | | | | | | |

## Live run log

### 2026-11-21: first local run (Olivia + Claude), commit `d75ff96`, Python 3.11, no DeepSeek key yet

| Check | Result |
|---|---|
| `pytest` | 35 passed |
| `try_profiles.py` (TF-IDF, sample deals) | all PASS (per the earlier handoff) |
| `try_profiles.py --retriever embed` (sample deals) | all PASS; MiniLM downloaded and Chroma ran. 0% overlap between the 3 users |
| `try_profiles.py --llm` | **not run**: no DEEPSEEK_API_KEY in .env yet |
| `python -m calendeal.sources.slickdeals` (live) | 25 real deals, dates correct (see below) |
| `python -m calendeal.main snapshot` (no local search) | 59 deals = 25 Slickdeals + 34 made-up samples; local_search 0 (needs the LLM) |
| `python -m app.app` (no key) | loads at phone width, shows "LLM: off (no key; using search only)" |
| DeepSeek config (offline) | `deepseek-flash` is a valid id per api-docs.deepseek.com; the request body carries `thinking: disabled` with tools bound |

Embed retriever, sample deals, top weekly picks (score):
- Foodie Fran: Date night movie tickets 0.572, Coffee half off 0.517, Taco Tuesday 0.496, Pizza 2-for-1 0.483
- Household Hank: Colgate BOGO 0.739, $2 off detergent 0.624, Car wash 5-pack 0.409, Paper towels 0.378
- Gamer Gwen: Switch game sale 0.689, Board game BOGO 0.557, Holiday gift sets 0.553, Gaming headset 0.498

Odd result: Gwen's example search "gift for my brother" ranks "Burrito bowl BOGO" and "Happy hour beer specials" 2nd and 3rd. The check passes because it only looks at the top hit.

**Slickdeals live feed problems (not tuned yet):**
- **Store is always "Online".** `STORE_RE` looks for "at Store" in the title, and front-page titles don't have it. The merchant link in each description does (bomgaars.com, walmart.com), so take the store from that domain.
- **Keyword categories misfire:** a LEGO pizza set was tagged `food`, a DeWalt impact driver `electronics`, fuel stabilizer `shopping` (should be `car`), Frndly TV `electronics` (should be `entertainment`).
- No promo codes were found in these 25 deals.
- The snapshot mixes the made-up `sample` deals in with the real ones. Leave `sample` out of the real demo snapshot.
