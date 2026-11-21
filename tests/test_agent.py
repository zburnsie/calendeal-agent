from datetime import date

import pytest
from langchain_core.messages import AIMessage

from calendeal import store
from calendeal.agent import CalenDealAgent
from calendeal.matcher import Pick, Picks, rerank_with_llm, search
from calendeal.models import UserProfile
from calendeal.sources import sample
from tests.fakes import ScriptedModel, StubStructured, tool_call

TODAY = date(2026, 11, 22)


@pytest.fixture(autouse=True)
def tmp_users(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "USERS", tmp_path / "users")


def pool():
    return sample.fetch()


def pizza_id():
    return next(d.deal_id for d in pool() if "Pizza" in d.title)


def test_search_uses_the_question_not_categories():
    p = UserProfile(name="t", categories=["food"])
    hits = search(pool(), p, "oil change", today=TODAY)
    assert hits and hits[0].category == "car"


def test_rerank_with_structured_output_sets_reasons():
    cands = pool()[:5]
    model = StubStructured(Picks(picks=[Pick(i=2, reason="you love this"), Pick(i=99, reason="bad index")]))
    out = rerank_with_llm(cands, UserProfile(name="t"), model=model)
    assert len(out) == 1 and out[0].reason == "you love this"


def test_agent_auto_mode_adds_without_asking():
    pid = pizza_id()
    model = ScriptedModel(script=[tool_call("add_to_calendar", {"deal_ids": [pid]}), AIMessage(content="Done!")])
    a = CalenDealAgent(UserProfile(name="Auto", hitl_mode="auto"), pool(), model=model, today=TODAY)
    out = a.chat("add the pizza deal")
    assert out["pending"] is None and out["reply"] == "Done!"
    assert [d.deal_id for d in store.calendar("Auto")] == [pid]


def test_agent_approve_mode_pauses_then_resumes():
    pid = pizza_id()
    model = ScriptedModel(script=[tool_call("add_to_calendar", {"deal_ids": [pid]}), AIMessage(content="Added it.")])
    a = CalenDealAgent(UserProfile(name="Approver", hitl_mode="approve"), pool(), model=model, today=TODAY)
    out = a.chat("add the pizza deal")
    assert out["pending"] and out["pending"][0].deal_id == pid
    assert store.calendar("Approver") == []            # nothing written before approval
    out = a.decide(approve=True)
    assert out["reply"] == "Added it."
    assert [d.deal_id for d in store.calendar("Approver")] == [pid]


def test_agent_reject_writes_nothing():
    pid = pizza_id()
    model = ScriptedModel(script=[tool_call("add_to_calendar", {"deal_ids": [pid]}), AIMessage(content="Okay, skipped.")])
    a = CalenDealAgent(UserProfile(name="Rejecter", hitl_mode="approve"), pool(), model=model, today=TODAY)
    a.chat("add pizza")
    a.decide(approve=False)
    assert store.calendar("Rejecter") == []


def test_agent_search_tool_runs():
    model = ScriptedModel(script=[tool_call("search_deals", {"query": "pizza"}), AIMessage(content="Found pizza.")])
    a = CalenDealAgent(UserProfile(name="S"), pool(), model=model, today=TODAY)
    assert a.chat("any pizza?")["reply"] == "Found pizza."


def test_agent_without_llm_falls_back_to_search(monkeypatch):
    monkeypatch.setenv("CALENDEAL_LLM", "deepseek:deepseek-flash")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    a = CalenDealAgent(UserProfile(name="NoKey"), pool(), today=TODAY)
    out = a.chat("pizza")
    assert "No LLM key" in out["reply"] and "Pizza" in out["reply"]


def test_store_remove_dismisses_and_rebuilds_ics():
    d = pool()[0]
    store.add("U", [d])
    assert d.deal_id in store.ics_path("U").read_text()
    store.remove("U", d.deal_id)
    assert d.deal_id not in store.ics_path("U").read_text()
    assert store.add("U", [d]) == []                   # dismissed deals never come back


def test_store_respects_weekly_limit():
    added = store.add("L", pool()[:10], limit=3)
    assert len(added) == 3
