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
| 4 | Run 3 + Claude rerank with reasons | The full agent |

Keep the snapshot and profiles fixed across runs. Record results in a table in this file, with the date and the git commit for each run.

`python -m calendeal.main match --snapshot latest --profile profiles/X.json --retriever tfidf|embed --no-llm` switches between runs.

## Results

| Run | Date | Commit | Precision@8 (avg) | Categories (avg) | Overlap | Unsafe on calendar |
|---|---|---|---|---|---|---|
| | | | | | | |
