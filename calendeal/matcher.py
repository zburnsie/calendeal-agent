"""Decide which deals fit which person. See docs/ARCHITECTURE.md, "Matching, step by step".

  1. Hard filters: middleware (expired / invalid / flagged links), intake categories, avoid list, brand loyalty.
  2. Retrieve: semantic search of the profile against the deals.
       "embed": sentence-transformers all-MiniLM-L6-v2 + Chroma (same as Lab 1)
       "tfidf": TF-IDF cosine similarity (no downloads; used by tests and as the fallback)
       "auto":  embed if chromadb + sentence-transformers are installed, else tfidf
  3. Boosts: favorite stores, preferred channel, loyal brand.
  4. Rerank: if an LLM key is set (DeepSeek by default, see llm.py), the model picks the final set
     and writes a "why you" line. Structured output via Pydantic, with a bounded retry.
"""
from __future__ import annotations

import json
import os
from datetime import date

from pydantic import BaseModel, Field

from calendeal import llm
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


def search(
    deals: list[Deal],
    profile: UserProfile,
    query: str,
    k: int = 6,
    retriever: str = "auto",
    today: date | None = None,
    respect_categories: bool = False,
) -> list[Deal]:
    """Semantic search for the chat agent: the user's question, not their whole profile, is the query.

    Still applies the safety filters (expired, flagged links), the avoid list and brand loyalty.
    Categories are NOT enforced by default: if they ask about tires, show tires.
    """
    if not respect_categories:
        profile = UserProfile(**{**profile.__dict__, "categories": []})
    deals = hard_filter(deals, profile, today)
    if not deals or not query.strip():
        return []
    if retriever == "auto":
        retriever = "embed" if _embed_available() else "tfidf"
    scores = _embed_scores(deals, query) if retriever == "embed" else _tfidf_scores(deals, query)
    for d, s in zip(deals, scores):
        d.score = round(s, 4)
    ranked = sorted(deals, key=lambda d: d.score, reverse=True)
    return [d for d in ranked if d.score > 0][:k]


# ---------- 4. rerank ----------

class Pick(BaseModel):
    i: int = Field(description="index of the deal in the candidate list")
    reason: str = Field(description="under 12 words, specific to this person")


class Picks(BaseModel):
    picks: list[Pick]


def rerank_prompt(candidates: list[Deal], profile: UserProfile) -> str:
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
    return (
        "You pick deals for a college student. Only pick deals on things they would buy anyway; "
        "don't push extra spending. Prefer variety over several deals from one store.\n"
        f"Profile: {json.dumps(about)}\n\n"
        f"Candidate deals:\n{listing}\n\n"
        f"Choose at most {profile.max_deals_per_week} that this person would actually use, best first, "
        "each with a short reason written to them."
    )


def rerank_with_llm(candidates: list[Deal], profile: UserProfile, use_llm: bool = True, model=None) -> list[Deal]:
    """LLM picks the final set and writes a 'why you' line. Falls back to retrieval order with no model."""
    if not use_llm or not candidates:
        return candidates[: profile.max_deals_per_week]
    result = llm.structured(Picks, rerank_prompt(candidates, profile), model=model)
    if result is None:
        return candidates[: profile.max_deals_per_week]

    chosen, seen = [], set()
    for p in result.picks:
        if 0 <= p.i < len(candidates) and p.i not in seen:
            seen.add(p.i)
            candidates[p.i].reason = p.reason[:120]
            chosen.append(candidates[p.i])
    return chosen[: profile.max_deals_per_week] or candidates[: profile.max_deals_per_week]


def match(
    deals: list[Deal],
    profile: UserProfile,
    retriever: str = "auto",
    use_llm: bool = True,
    today: date | None = None,
    model=None,
) -> list[Deal]:
    return rerank_with_llm(retrieve(deals, profile, retriever=retriever, today=today), profile, use_llm, model)
