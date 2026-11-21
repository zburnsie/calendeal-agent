"""CalenDeal v1 web app (Gradio, mobile-first). Run from the repo root:

    python -m app.app            # then open http://127.0.0.1:7860 (use your browser's phone view for the demo)

Tabs:
  1. Start      Pinterest-style intake: tap categories, add details, choose auto vs. approve
  2. This week  "What we learned about you" + this week's picks as cards; tap to approve
  3. Calendar   what's on your CalenDeal calendar, remove a deal, download the .ics
  4. Chat       ask the agent ("cheap pizza tonight?"), approve calendar adds right in the chat

Deals come from the latest snapshot in data/snapshots/ if there is one, otherwise the sources
(sample deals + Slickdeals RSS; local web search if CALENDEAL_LOCAL_SEARCH=1).
Set CALENDEAL_TODAY=2026-11-22 to demo an old snapshot as if it were that day.
"""
from __future__ import annotations

import html
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gradio as gr  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from calendeal import llm, matcher, store  # noqa: E402
from calendeal.agent import CalenDealAgent  # noqa: E402
from calendeal.models import CATEGORIES, MAX_DEALS_CAP, Deal, UserProfile  # noqa: E402

load_dotenv(ROOT / ".env")

CATEGORY_LABELS = {
    "food": "🍕 Food & restaurants", "grocery": "🛒 Groceries & household", "clothing": "👕 Clothing",
    "electronics": "🎧 Electronics", "entertainment": "🎬 Movies & fun", "car": "🚗 Car care & gas",
    "home": "🏠 Home", "health & beauty": "🪥 Health & beauty", "gifts": "🎁 Gifts", "shopping": "🛍️ General / online",
}
LABEL_TO_CAT = {v: k for k, v in CATEGORY_LABELS.items()}
DEMO_PROFILES = {p.stem: p for p in sorted((ROOT / "profiles").glob("*.json"))}

CSS = """
.gradio-container {max-width: 520px !important; margin: 0 auto !important;}
.deal {border: 1px solid var(--border-color-primary); border-radius: 14px; padding: 12px 14px; margin: 8px 0;
       background: var(--background-fill-secondary);}
.deal h4 {margin: 0 0 4px 0; font-size: 1.05em;}
.deal .meta {opacity: .75; font-size: .88em;}
.deal .why {margin-top: 6px; font-style: italic;}
.badge {display: inline-block; border-radius: 999px; padding: 1px 9px; font-size: .8em; margin: 6px 6px 0 0;
        background: var(--color-accent-soft); }
.badge.warn {background: #fde68a; color: #78350f;}
.empty {opacity: .7; text-align: center; padding: 18px;}
"""


# ---------- data ----------

def today() -> date | None:
    t = os.getenv("CALENDEAL_TODAY")
    return date.fromisoformat(t) if t else None


def load_pool() -> tuple[list[Deal], str]:
    from calendeal import snapshot

    try:
        deals = snapshot.load("latest")
        return deals, f"{len(deals)} deals from snapshot {snapshot.resolve('latest').stem}"
    except SystemExit:
        from calendeal.sources import fetch_all

        names = os.getenv("CALENDEAL_APP_SOURCES", "sample,slickdeals,local_search").split(",")
        deals = fetch_all(names)
        return deals, f"{len(deals)} deals from live sources ({', '.join(names)})"


POOL, POOL_NOTE = load_pool()


# ---------- rendering ----------

def card(d: Deal) -> str:
    e = html.escape
    when = f"{d.start:%a %b %d}" + (f" – {d.end:%a %b %d}" if d.end != d.start else "")
    badges = [f'<span class="badge">{e(d.category or "deal")}</span>', f'<span class="badge">{e(d.channel)}</span>']
    if d.promo_code:
        badges.append(f'<span class="badge">code <b>{e(d.promo_code)}</b></span>')
    if d.url and d.link_safe is None:
        badges.append('<span class="badge warn">link not checked</span>')
    link = f' · <a href="{e(d.url)}" target="_blank" rel="noopener">open</a>' if d.url else ""
    why = f'<div class="why">Why you: {e(d.reason)}</div>' if d.reason else ""
    desc = f"<div>{e(d.description[:180])}</div>" if d.description else ""
    return (f'<div class="deal"><h4>{e(d.title)}</h4><div class="meta">{e(d.store)} · {when}{link}</div>'
            f'{desc}{why}{"".join(badges)}</div>')


def cards(deals: list[Deal], empty: str) -> str:
    return "".join(card(d) for d in deals) if deals else f'<div class="empty">{empty}</div>'


def choice_label(d: Deal) -> str:
    return f"{d.title} @ {d.store} ({d.start:%b %d})"


def about_md(p: UserProfile) -> str:
    rows = [
        ("Categories", ", ".join(CATEGORY_LABELS.get(c, c) for c in p.categories) or "all"),
        ("Interests", ", ".join(p.interests) or "—"),
        ("Favorite stores", ", ".join(p.stores) or "—"),
        ("Brand loyal", ", ".join(f"{b} {k}" for k, b in p.brand_loyal.items()) or "any brand is fine"),
        ("Never show", ", ".join(p.avoid) or "—"),
        ("Where", f"{p.location or '—'} (within {p.radius_miles} mi)" + (" · prefers online" if p.prefers_online else "")),
        ("Calendar", f"{'adds automatically' if p.hitl_mode == 'auto' else 'asks you first'}, up to {p.max_deals_per_week}/week"),
    ]
    if p.notes:
        rows.append(("Notes", p.notes))
    return "#### What we learned about you\n" + "\n".join(f"- **{k}:** {v}" for k, v in rows) + \
        "\n\n_Change any of this on the **Start** tab._"


# ---------- intake ----------

def parse_list(s: str) -> list[str]:
    return [x.strip() for x in (s or "").replace("\n", ",").split(",") if x.strip()]


def parse_brands(s: str) -> dict[str, str]:
    out = {}
    for item in parse_list(s):
        if ":" in item:
            product, brand = item.split(":", 1)
            if product.strip() and brand.strip():
                out[product.strip().lower()] = brand.strip()
    return out


def profile_to_form(p: UserProfile):
    return (
        p.name, [CATEGORY_LABELS[c] for c in p.categories if c in CATEGORY_LABELS], ", ".join(p.interests),
        ", ".join(p.stores), ", ".join(f"{k}: {v}" for k, v in p.brand_loyal.items()), ", ".join(p.avoid),
        p.notes, p.location, p.radius_miles, p.prefers_online,
        "Ask me first" if p.hitl_mode == "approve" else "Add automatically", p.max_deals_per_week,
    )


def load_existing(choice: str):
    if not choice:
        return [gr.update()] * 12
    if choice in DEMO_PROFILES:
        p = UserProfile.load(DEMO_PROFILES[choice])
    else:
        p = store.load_profile(choice)
    return profile_to_form(p) if p else [gr.update()] * 12


# ---------- core actions ----------

def build_session(p: UserProfile) -> dict:
    return {"profile": p, "agent": CalenDealAgent(p, list(POOL), today=today()), "picks": []}


def find_deals(session: dict):
    p: UserProfile = session["profile"]
    picks = matcher.match(POOL, p, today=today())
    session["picks"] = picks
    added_note = ""
    if p.hitl_mode == "auto":
        added = store.add(p.name, picks, limit=p.max_deals_per_week)
        added_note = f"✅ Added {len(added)} new deal(s) to your calendar automatically."
        choices = gr.update(choices=[], value=[], visible=False)
        add_btn = gr.update(visible=False)
    else:
        on_cal = {d.deal_id for d in store.calendar(p.name)}
        opts = [(choice_label(d), d.deal_id) for d in picks if d.deal_id not in on_cal]
        choices = gr.update(choices=opts, value=[v for _, v in opts], visible=bool(opts))
        add_btn = gr.update(visible=bool(opts))
        added_note = "Tap to un-select anything you don't want, then add." if opts else ""
    return cards(picks, "No deals matched yet. Try more categories or interests."), choices, add_btn, added_note


def save_and_find(name, cats, interests, stores, brands, avoid, notes, location, radius, online, mode, limit):
    if not (name or "").strip():
        raise gr.Error("Add your name first.")
    p = UserProfile(
        name=name.strip(), categories=[LABEL_TO_CAT[c] for c in cats or []], interests=parse_list(interests),
        stores=parse_list(stores), brand_loyal=parse_brands(brands), avoid=parse_list(avoid), notes=notes or "",
        location=location or "", radius_miles=int(radius), prefers_online=bool(online),
        hitl_mode="approve" if mode == "Ask me first" else "auto", max_deals_per_week=int(limit),
    )
    store.save_profile(p)
    session = build_session(p)
    picks_html, choices, add_btn, note = find_deals(session)
    return (session, about_md(p), picks_html, choices, add_btn, note, *calendar_view(session),
            [], gr.update(visible=False), gr.Tabs(selected="week"))


def add_selected(session: dict, ids: list[str]):
    if not session:
        raise gr.Error("Fill out the Start tab first.")
    p = session["profile"]
    chosen = [d for d in session["picks"] if d.deal_id in set(ids or [])]
    added = store.add(p.name, chosen, limit=p.max_deals_per_week)
    picks_html, choices, add_btn, _ = find_deals(session)
    return (picks_html, choices, add_btn, f"✅ Added {len(added)} deal(s) to your calendar.", *calendar_view(session))


def calendar_view(session: dict):
    if not session:
        return cards([], "Nothing yet."), gr.update(choices=[]), None
    p = session["profile"]
    deals = sorted(store.calendar(p.name), key=lambda d: d.start)
    return (
        cards(deals, "Nothing on your CalenDeal calendar yet."),
        gr.update(choices=[(choice_label(d), d.deal_id) for d in deals], value=[]),
        str(store.ics_path(p.name)),
    )


def remove_selected(session: dict, ids: list[str]):
    if not session:
        raise gr.Error("Fill out the Start tab first.")
    for i in ids or []:
        store.remove(session["profile"].name, i)
    return calendar_view(session)


# ---------- chat ----------

def chat(session: dict, message: str, history: list):
    if not session:
        raise gr.Error("Fill out the Start tab first.")
    if not (message or "").strip():
        return history, "", gr.update(), gr.update()
    out = session["agent"].chat(message)
    history = (history or []) + [{"role": "user", "content": message}, {"role": "assistant", "content": out["reply"]}]
    return (history, "", *pending_view(out))


def pending_view(out: dict):
    if out.get("pending"):
        return gr.update(value=cards(out["pending"], ""), visible=True), gr.update(visible=True)
    return gr.update(value="", visible=False), gr.update(visible=False)


def decide(session: dict, approve: bool, history: list):
    out = session["agent"].decide(approve)
    history = (history or []) + [{"role": "assistant", "content": out["reply"]}]
    return (history, *pending_view(out), *calendar_view(session))


# ---------- layout ----------

def build() -> gr.Blocks:
    with gr.Blocks(title="CalenDeal") as demo:
        session = gr.State(None)
        gr.Markdown("## 📅 CalenDeal\nSave on what you already buy. Deals that fit you, on your calendar.")
        llm_note = f"LLM: `{llm.model_name()}`" if llm.available() else "LLM: off (no key; using search only)"
        gr.Markdown(f"<small>{POOL_NOTE} · {llm_note}</small>")

        with gr.Tabs() as tabs:
            with gr.Tab("Start", id="start"):
                existing = gr.Dropdown(choices=list(DEMO_PROFILES) + store.list_users(), label="Load a demo or saved profile",
                                       value=None, allow_custom_value=False)
                name = gr.Textbox(label="Your name", placeholder="Emma")
                cats = gr.CheckboxGroup(choices=list(CATEGORY_LABELS.values()), label="What do you spend on? Tap all that apply")
                interests = gr.Textbox(label="Anything specific?", placeholder="pizza, running shoes, oil change, Christmas gifts")
                with gr.Accordion("More details (optional)", open=False):
                    stores_in = gr.Textbox(label="Favorite stores", placeholder="Maverik, Old Navy")
                    brands = gr.Textbox(label="Brands you always buy (product: brand)", placeholder="detergent: Tide, toothpaste: Crest")
                    avoid = gr.Textbox(label="Never show me", placeholder="alcohol, gym memberships")
                    notes = gr.Textbox(label="Notes for the agent", lines=2, placeholder="Looking for Black Friday TV deals")
                    online = gr.Checkbox(label="I mostly shop online")
                location = gr.Textbox(label="City or ZIP", value="Provo, UT")
                radius = gr.Slider(1, 50, value=15, step=1, label="How far will you go? (miles)")
                mode = gr.Radio(["Ask me first", "Add automatically"], value="Ask me first", label="Adding to your calendar")
                limit = gr.Slider(1, MAX_DEALS_CAP, value=8, step=1, label="Most deals per week")
                go = gr.Button("Save & find my deals", variant="primary")

            with gr.Tab("This week", id="week"):
                about = gr.Markdown("Fill out **Start** first.")
                picks_html = gr.HTML()
                pick_choices = gr.CheckboxGroup(label="Add to my calendar", visible=False)
                add_btn = gr.Button("Add selected to calendar", variant="primary", visible=False)
                week_note = gr.Markdown()
                refresh = gr.Button("Refresh picks")

            with gr.Tab("Calendar", id="cal"):
                gr.Markdown("Download the file and open it: it imports into **Apple Calendar** or **Google Calendar** "
                            "(Google: Settings → Import & export). Everything lands on one CalenDeal calendar, so "
                            "you can hide all deals at once.")
                ics_file = gr.File(label="Your CalenDeal calendar (.ics)", interactive=False)
                cal_html = gr.HTML()
                remove_choices = gr.CheckboxGroup(label="Remove from calendar")
                remove_btn = gr.Button("Remove selected")

            with gr.Tab("Chat", id="chat"):
                bot = gr.Chatbot(height=420, label="CalenDeal agent")
                pending_html = gr.HTML(visible=False)
                with gr.Row(visible=False) as approve_row:
                    yes = gr.Button("✅ Approve", variant="primary")
                    no = gr.Button("✖ No thanks")
                msg = gr.Textbox(placeholder="Any cheap pizza deals this weekend?", show_label=False)
                gr.Examples(["What are my best deals this week?", "Any deals on detergent?",
                             "Add the pizza deal to my calendar", "What's on my calendar?",
                             "Look for oil change deals near me"], inputs=msg)

        form = [name, cats, interests, stores_in, brands, avoid, notes, location, radius, online, mode, limit]
        existing.change(load_existing, existing, form)
        go.click(save_and_find, form,
                 [session, about, picks_html, pick_choices, add_btn, week_note, cal_html, remove_choices, ics_file,
                  bot, approve_row, tabs])
        add_btn.click(add_selected, [session, pick_choices],
                      [picks_html, pick_choices, add_btn, week_note, cal_html, remove_choices, ics_file])
        refresh.click(lambda s: find_deals(s) if s else (gr.update(),) * 4, session,
                      [picks_html, pick_choices, add_btn, week_note])
        remove_btn.click(remove_selected, [session, remove_choices], [cal_html, remove_choices, ics_file])
        msg.submit(chat, [session, msg, bot], [bot, msg, pending_html, approve_row])
        yes.click(lambda s, h: decide(s, True, h), [session, bot],
                  [bot, pending_html, approve_row, cal_html, remove_choices, ics_file])
        no.click(lambda s, h: decide(s, False, h), [session, bot],
                 [bot, pending_html, approve_row, cal_html, remove_choices, ics_file])
    return demo


if __name__ == "__main__":
    build().launch(theme=gr.themes.Soft(), css=CSS, server_name=os.getenv("HOST", "127.0.0.1"),
                   server_port=int(os.getenv("PORT", "7860")), allowed_paths=[str(ROOT / "data")])
