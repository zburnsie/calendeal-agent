"""Phase 1b: decide which deals fit which person.

Two steps (the "RAG" part):
  1. Retrieve: score every deal against the profile with TF-IDF cosine similarity, keep the top N.
  2. Generate: if ANTHROPIC_API_KEY is set, Claude picks the final set from those candidates
     and writes a one-line reason for each. Otherwise we keep the retrieval ranking.

Swap step 1 for embeddings (OpenAI, sentence-transformers, Chroma) later if TF-IDF isn't good enough.
"""
from __future__ import annotations

import json
import os
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from calendeal.models import Deal, UserProfile


def retrieve(deals: list[Deal], profile: UserProfile, top_n: int = 15) -> list[Deal]:
    if not deals:
        return []
    avoid = [a.lower() for a in profile.avoid]
    deals = [d for d in deals if not any(a in d.text().lower() for a in avoid)]
    if not deals:
        return []

    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vec.fit_transform([profile.text()] + [d.text() for d in deals])
    sims = cosine_similarity(matrix[0:1], matrix[1:]).ravel()

    for d, s in zip(deals, sims):
        bonus = 0.15 if any(st.lower() in d.store.lower() for st in profile.stores) else 0.0
        if profile.prefers_online and "online" in d.channel.lower():
            bonus += 0.05
        d.score = round(float(s) + bonus, 4)

    ranked = sorted(deals, key=lambda d: d.score, reverse=True)
    return [d for d in ranked if d.score > 0][:top_n]


def rerank_with_llm(candidates: list[Deal], profile: UserProfile) -> list[Deal]:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key or not candidates:
        return candidates[: profile.max_deals_per_week]

    import anthropic

    listing = "\n".join(
        f"{i}. {d.title} @ {d.store} ({d.category}, {d.channel}, {d.start}–{d.end}) {d.description}"
        for i, d in enumerate(candidates)
    )
    prompt = (
        f"You pick deals for a college student.\n"
        f"Profile: {json.dumps(profile.__dict__)}\n\n"
        f"Candidate deals:\n{listing}\n\n"
        f"Choose at most {profile.max_deals_per_week} that this person would actually use. "
        'Reply with only JSON: [{"i": <number>, "reason": "<under 12 words>"}]'
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

    chosen = []
    for p in picks:
        i = int(p["i"])
        if 0 <= i < len(candidates):
            candidates[i].reason = p.get("reason", "")
            chosen.append(candidates[i])
    return chosen


def match(deals: list[Deal], profile: UserProfile) -> list[Deal]:
    return rerank_with_llm(retrieve(deals, profile), profile)
