"""Decide which deals fit which person. See docs/ARCHITECTURE.md, "Matching, step by step".

  1. Hard filters: middleware (expired / invalid / flagged links), intake categories, avoid list, brand loyalty.
  2. Retrieve: semantic search of the profile against the deals.
       "embed": sentence-transformers all-MiniLM-L6-v2 + Chroma (same as Lab 1)
       "tfidf": TF-IDF cosine similarity (no downloads; used by tests and as the fallback)
       "auto":  embed if chromadb + sentence-transformers are installed, else tfidf
  3. Boosts: favorite stores, preferred channel, loyal brand.
  4. Rerank: if ANTHROPIC_API_KEY is set, Claude picks the final set and writes a "why you" line.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date

from calendeal.middleware import clean
from calendeal.models import Deal, UserProfile

EMBED_MODEL = os.getenv("CALENDEAL_EMBED_MODEL", "all-MiniLM-L6-v2")


# ---------- 1. hard filters ----------

def hard_filter(deals: list[Deal], profile: UserProfile, today: date | None = None) -> list[Deal]:
    deals = clean(deals, today)
    if profile.categories:
        deals = [d for d in deals if not d.category or d.category.lower() in profile.categories]
    avoid = [a.lower() for a in profile.avoid]
    deals = [d for d in deals if not any(a in d.text().lower() for a in avoid)]
    loyal = {k.lower(): v.lower() for k, v in profile.brand_loyal.items()}
    deals = [
        d for d in deals
        if not (d.product_type.lower() in loyal and d.brand and d.brand.lower() != loyal[d.product_type.lower()])
    ]
    return deals


# ---------- 2. retrieve ----------

def _tfidf_scores(deals: list[Deal], query: str) -> list[float]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vec.fit_transform([query] + [d.text() for d in deals])
    return [float(s) for s in cosine_similarity(matrix[0:1], matrix[1:]).ravel()]


def _embed_scores(deals: list[Deal], query: str) -> list[float]:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
    try:
        client.delete_collection("deals")
    except Exception:
        pass
    col = client.create_collection(
        "deals",
        embedding_function=SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL),
        metadata={"hnsw:space": "cosine"},
    )
    ids = [f"{i}" for i in range(len(deals))]
    col.add(ids=ids, documents=[d.text() for d in deals])
    res = col.query(query_texts=[query], n_results=len(deals))
    sim = {i: 1.0 - dist for i, dist in zip(res["ids"][0], res["distances"][0])}
    return [sim.get(i, 0.0) for i in ids]


def _embed_available() -> bool:
    try:
        import chromadb  # noqa: F401
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def retrieve(
    deals: list[Deal],
    profile: UserProfile,
    top_n: int = 15,
    retriever: str = "auto",
    today: date | None = None,
) -> list[Deal]:
    deals = hard_filter(deals, profile, today)
    if not deals:
        return []

    if retriever == "auto":
        retriever = "embed" if _embed_available() else "tfidf"
    scores = _embed_scores(deals, profile.text()) if retriever == "embed" else _tfidf_scores(deals, profile.text())

    # ---------- 3. boosts ----------
    loyal_brands = {v.lower() for v in profile.brand_loyal.values()}
    for d, s in zip(deals, scores):
        bonus = 0.0
        if any(st.lower() in d.store.lower() for st in profile.stores):
            bonus += 0.15
        if d.brand and d.brand.lower() in loyal_brands:
            bonus += 0.15
        if profile.prefers_online and "online" in d.channel.lower():
            bonus += 0.05
        d.score = round(s + bonus, 4)

    ranked = sorted(deals, key=lambda d: d.score, reverse=True)
    return [d for d in ranked if d.score > 0][:top_n]


# ---------- 4. rerank ----------

def rerank_with_llm(candidates: list[Deal], profile: UserProfile, use_llm: bool = True) -> list[Deal]:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not use_llm or not key or not candidates:
        return candidates[: profile.max_deals_per_week]

    import anthropic

    listing = "\n".join(
        f"{i}. {d.title} @ {d.store} ({d.category}, {d.channel}, {d.start}–{d.end})"
        f"{' code ' + d.promo_code if d.promo_code else ''} {d.description[:200]}"
        for i, d in enumerate(candidates)
    )
    about = {
        "interests": profile.interests, "categories": profile.categories, "stores": profile.stores,
        "brand_loyal": profile.brand_loyal, "notes": profile.notes, "location": profile.location,
        "prefers_online": profile.prefers_online,
    }
    prompt = (
        "You pick deals for a college student. Only pick deals on things they would buy anyway; "
        "don't push extra spending. Prefer variety over five deals from one store.\n"
        f"Profile: {json.dumps(about)}\n\n"
        f"Candidate deals:\n{listing}\n\n"
        f"Choose at most {profile.max_deals_per_week} that this person would actually use. "
        'Reply with only JSON: [{"i": <number>, "reason": "<under 12 words, specific to this person>"}]'
    )
    client = anthropic.Anthropic(api_key=key)
    msg = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    try:
        picks = json.loads(re.search(r"\[.*\]", text, re.S).group(0))
    except Exception:
        print("[warn] couldn't parse LLM response; using retrieval order")
        return candidates[: profile.max_deals_per_week]

    chosen, seen = [], set()
    for p in picks:
        i = int(p.get("i", -1))
        if 0 <= i < len(candidates) and i not in seen:
            seen.add(i)
            candidates[i].reason = str(p.get("reason", ""))[:120]
            chosen.append(candidates[i])
    return chosen[: profile.max_deals_per_week]


def match(
    deals: list[Deal],
    profile: UserProfile,
    retriever: str = "auto",
    use_llm: bool = True,
    today: date | None = None,
) -> list[Deal]:
    return rerank_with_llm(retrieve(deals, profile, retriever=retriever, today=today), profile, use_llm)
