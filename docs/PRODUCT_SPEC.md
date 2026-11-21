# CalenDeal — Product Spec

Source: team kickoff meeting transcript (Nov 2026). Where the transcript was unclear, the call made here is marked **(assumed)**, so the team can overrule it.

## Problem

People miss out on saving money on things they **already buy and already do**. Deals run out, coupons expire in a drawer, promo codes get forgotten at checkout, and the good local deals are scattered across sites, mailers, and Facebook groups.

> We are not trying to get people to spend more. We help them spend less on what they were going to buy anyway.

One-line problem statement for slides:
**"Students miss deals on things they already buy because deals are scattered, and the ones they do find expire before they use them."**

### Market numbers mentioned in the meeting (verify before presenting)

| Claim | Status |
|---|---|
| ~82% of Americans say they've missed a deal because they forgot a promo code, coupon, cashback offer, or loyalty points | Source not recorded. **Find and cite it before it goes on a slide.** |
| ~38% (about 2 in 5) lose more than $100/year this way | Source not recorded. Verify. |
| "About $10 billion" in missed savings | Back-of-envelope math done live in the meeting, and the team flagged it as iffy. Redo the math from the cited numbers, or drop it. |

The professor's rubric favors "depth of understanding over surface appeal": a well-justified problem beats an impressive-sounding one. Cite real sources.

## Who it's for

College students in Provo / Utah County (demo region). Two kinds of saver show up in the demo:

- **Eats-out saver**: restaurants, fast food, coffee, entertainment.
- **Grocery/household saver**: groceries, detergent, toothpaste, oil changes, brand-loyal staples.

## What the user gets (v1)

1. **Intake (Pinterest-style).** Tap the categories you care about (Food, Groceries, Clothing, Electronics, Entertainment, Car care, Home, Gifts…), then narrower picks inside each. Then an optional free-text box / short chat: "I'm looking for Black Friday TV deals" or "I always buy Tide."
   - Checkboxes are on purpose: they surface things people wouldn't think to type, and they become structured categories the matcher can filter on.
2. **"What we learned about you" page.** Shows the profile the agent built from the intake. The user can add or remove anything.
3. **Weekly deals → calendar.** Once a week, the agent picks the deals that fit and puts them on a dedicated **CalenDeal calendar** that works with **Apple and Google** (subscribable `.ics` feed or `.ics` download). Each event has:
   - what the deal is, where, and when it expires
   - a one-line "why you" reason
   - **the promo code and link** for online deals, so there's no hunting at checkout (tier 2)
   - a reminder before it expires
4. **Human-in-the-loop toggle.**
   - *Auto*: deals go straight on the calendar.
   - *Approve first*: the agent shows deal cards, and you tap the ones you want ("tap, tap, boom, put these on my calendar").
5. **Weekly limit.** The user picks the most deals per week they want (default 8, max ~20) so the calendar isn't flooded.
6. **Chat with the agent.** "What deals near me this weekend for pizza?" It answers from the stored deals (RAG) and can add a deal to the calendar.

After intake, the app should work without the user opening it again. The UI is for adjusting, approving, and asking.

## Platform

- **v1: web app, mobile-first layout.** Build in the browser, demo it in a phone-sized view.
- Later, maybe: Chrome extension or a native mobile wrapper. Not in scope for the class.

## The demo we're building toward

The goal is a convincing proof of concept, not a product that covers the whole internet.

- One **"mega scrape"**: pull one week of real deals for Provo/Utah plus national online deals, and store them as a snapshot.
- Run that snapshot through link-safety and expiry checks once.
- Show **2–3 different user profiles** getting clearly different calendars from the same deal pool.
- Show the approve-first flow and the resulting calendar on a phone screen.

## Why it needs an agent (for the Agentic Opportunities Matrix)

A plain chatbot can answer "find me deals." What CalenDeal adds:

- It matches deals to *your* profile and history instead of returning generic "deals near me".
- It is time-aware: it schedules around expiry dates and reminds you.
- It acts: it writes to your calendar, with an approval step you control.
- It runs weekly without being asked.

The team agreed most of the value is the **smooth experience**. Polish the core flow before adding features.
