"""The CalenDeal chat agent (Tier 1.7): one agent, RAG over the week's deals, tools to act on the calendar.

Pattern from the labs:
  - init_chat_model via calendeal.llm (DeepSeek by default)
  - langchain.agents.create_agent with @tool functions
  - HumanInTheLoopMiddleware on add_to_calendar when the user's hitl_mode is "approve"
    (same middleware as middlewareHITLMAS.py; the UI shows Approve / Reject and resumes the graph)
  - InMemorySaver checkpointer so interrupts can be resumed, keyed by thread_id

Tools:
  search_deals          semantic search over this week's deal pool (the "R" in RAG)
  weekly_picks          the matcher's picks for this profile
  find_local_deals      targeted live web search ("look extra hard for X") — adds to the pool
  add_to_calendar       writes to the CalenDeal calendar (paused for approval in approve mode)
  remove_from_calendar  takes a deal off the calendar and never suggests it again
  my_calendar           what's on the calendar now
"""
from __future__ import annotations

from datetime import date

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from calendeal import llm, matcher, store
from calendeal.models import Deal, UserProfile

SYSTEM_PROMPT = """You are CalenDeal, a deal assistant for a college student in {location}.
Your job: help them save money on things they ALREADY buy, and put the deals they want on their
CalenDeal calendar. Never push extra spending.

What you know about them: {about}
Today is {today}. Calendar: {n_on_cal} deal(s) on it, weekly limit {limit}.

Rules:
- Only talk about deals returned by your tools. Never invent a deal, store, price, date, or code.
  If the tools find nothing, say so and offer to search the web for local deals (find_local_deals).
- When you mention a deal, include its id in square brackets, e.g. [3f2a9c1e0b7d4a11], so the app can show it.
- Keep replies short: a sentence of context, then a short list of deals with why each fits them.
- Before adding to the calendar, make sure they asked to add (or clearly agreed). Add by id.
- Never buy anything, ask for payment info, or message anyone on their behalf.
"""


def _about(profile: UserProfile) -> str:
    bits = []
    if profile.categories:
        bits.append("cares about " + ", ".join(profile.categories))
    if profile.interests:
        bits.append("interests: " + ", ".join(profile.interests))
    if profile.stores:
        bits.append("favorite stores: " + ", ".join(profile.stores))
    if profile.brand_loyal:
        bits.append("brand loyal: " + ", ".join(f"{b} {p}" for p, b in profile.brand_loyal.items()))
    if profile.avoid:
        bits.append("never show: " + ", ".join(profile.avoid))
    if profile.notes:
        bits.append(f"notes: {profile.notes}")
    return "; ".join(bits) or "nothing yet"


def _fmt(deals: list[Deal]) -> str:
    if not deals:
        return "No matching deals."
    lines = []
    for d in deals:
        line = d.short()
        if d.reason:
            line += f" — {d.reason}"
        if d.description:
            line += f"\n    {d.description[:160]}"
        if d.link_safe is None and d.url:
            line += "\n    (link not safety-checked yet)"
        lines.append(line)
    return "\n".join(lines)


class CalenDealAgent:
    """Holds one user's agent, deal pool, and conversation thread."""

    def __init__(self, profile: UserProfile, pool: list[Deal], model=None, today: date | None = None,
                 thread_id: str | None = None):
        self.profile = profile
        self.pool = pool
        self.today = today
        self.thread_id = thread_id or f"{store.slug(profile.name)}-chat"
        self.model = model if model is not None else llm.get_model(temperature=0.3)
        self.graph = self._build() if self.model is not None else None

    # ----- tools (closures so they see this user's profile and pool) -----
    def _tools(self):
        agent = self

        def by_ids(ids: list[str]) -> list[Deal]:
            wanted = {i.strip("[] ") for i in ids}
            return [d for d in agent.pool if d.deal_id in wanted]

        @tool
        def search_deals(query: str) -> str:
            """Search this week's deals for what the user is asking about (e.g. 'cheap pizza tonight',
            'oil change', 'detergent'). Returns matching deals with their ids."""
            return _fmt(matcher.search(agent.pool, agent.profile, query, k=6, today=agent.today))

        @tool
        def weekly_picks() -> str:
            """The deals picked for this user this week based on their profile, with reasons."""
            picks = matcher.match(agent.pool, agent.profile, today=agent.today, model=agent.model)
            return _fmt(picks)

        @tool
        def find_local_deals(request: str) -> str:
            """Search the web right now for local deals near the user, for a specific request
            ('Black Friday TV deals', 'cheap haircut'). Slower; use when search_deals finds nothing."""
            from calendeal.sources import local_search

            found = local_search.search(
                categories=agent.profile.categories or None, location=agent.profile.location or local_search.LOCATION,
                extra=request, today=agent.today, model=agent.model,
            )
            from calendeal.middleware import clean
            found = clean(found, agent.today)
            known = {d.deal_id for d in agent.pool}
            agent.pool.extend(d for d in found if d.deal_id not in known)
            return _fmt(found[:6]) if found else "The web search found no specific local deals for that."

        @tool
        def add_to_calendar(deal_ids: list[str]) -> str:
            """Add deals to the user's CalenDeal calendar by id. Only call when the user asked for it."""
            deals = by_ids(deal_ids)
            if not deals:
                return "None of those ids are in this week's deals."
            added = store.add(agent.profile.name, deals, limit=agent.profile.max_deals_per_week)
            skipped = len(deals) - len(added)
            msg = f"Added {len(added)} deal(s) to the CalenDeal calendar."
            if skipped:
                msg += f" Skipped {skipped} (already on it, dismissed, or weekly limit reached)."
            return msg

        @tool
        def remove_from_calendar(deal_id: str) -> str:
            """Remove a deal from the user's CalenDeal calendar (and don't suggest it again)."""
            ok = store.remove(agent.profile.name, deal_id.strip("[] "))
            return "Removed." if ok else "That deal wasn't on the calendar."

        @tool
        def my_calendar() -> str:
            """List the deals currently on the user's CalenDeal calendar."""
            return _fmt(store.calendar(agent.profile.name))

        return [search_deals, weekly_picks, find_local_deals, add_to_calendar, remove_from_calendar, my_calendar]

    def _build(self):
        middleware = []
        if self.profile.hitl_mode == "approve":
            middleware.append(HumanInTheLoopMiddleware(
                interrupt_on={"add_to_calendar": {"allowed_decisions": ["approve", "reject"]}},
                description_prefix="Add these deals to your CalenDeal calendar?",
            ))
        prompt = SYSTEM_PROMPT.format(
            location=self.profile.location or "Provo, UT",
            about=_about(self.profile),
            today=(self.today or date.today()).strftime("%A %B %d, %Y"),
            n_on_cal=len(store.calendar(self.profile.name)),
            limit=self.profile.max_deals_per_week,
        )
        return create_agent(self.model, tools=self._tools(), system_prompt=prompt,
                            middleware=middleware, checkpointer=InMemorySaver())

    # ----- running it -----
    @property
    def config(self) -> dict:
        return {"configurable": {"thread_id": self.thread_id}}

    def _result(self, result: dict) -> dict:
        """{'reply': str, 'pending': [deals awaiting approval] | None}"""
        if "__interrupt__" in result:
            value = result["__interrupt__"][0].value
            requests = value.get("action_requests", []) if isinstance(value, dict) else []
            ids = []
            for r in requests:
                ids += r.get("args", {}).get("deal_ids", [])
            self._n_pending = max(len(requests), 1)
            pending = [d for d in self.pool if d.deal_id in {i.strip("[] ") for i in ids}]
            return {"reply": "Want me to add these to your calendar?", "pending": pending}
        return {"reply": result["messages"][-1].text, "pending": None}

    def chat(self, message: str) -> dict:
        if self.graph is None:
            # No LLM key: still useful. Plain semantic search, no generation.
            hits = matcher.search(self.pool, self.profile, message, k=6, today=self.today)
            return {"reply": "(No LLM key set, so here are the closest matching deals.)\n\n" + _fmt(hits),
                    "pending": None}
        return self._result(self.graph.invoke({"messages": [{"role": "user", "content": message}]}, self.config))

    def decide(self, approve: bool, reason: str = "") -> dict:
        decision = {"type": "approve"} if approve else {"type": "reject", "message": reason or "User said no."}
        decisions = [decision] * getattr(self, "_n_pending", 1)  # one decision per paused tool call
        self._n_pending = 0
        return self._result(self.graph.invoke(Command(resume={"decisions": decisions}), self.config))
