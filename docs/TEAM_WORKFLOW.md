# How we work together

5 people, 3 weeks, everyone building with Claude. We don't split the app into fixed parts per person. We **take turns** on the code and keep each other updated.

## The loop

1. **Claim it in the group chat before you start.** "I'm working on the Gradio intake screen, tonight 8–10pm." That way two people (and two Claudes) don't edit the same files at once, which causes nasty merge conflicts.
2. **Pull first:** `git checkout main && git pull`, then make a branch: `git checkout -b <your-name>/<thing>`.
3. **Point your Claude at the docs.** It should read `CLAUDE.md` first. That file tells it to read these docs and the latest handoff.
4. **Work on one Tier item at a time** (`docs/PRIORITIES.md`).
5. **Before you stop:**
   - Run `pytest`.
   - Add an entry at the top of `docs/HANDOFF.md`: what you/your Claude did, what's left, anything broken, what's next.
   - Update the status column in `docs/PRIORITIES.md`.
   - Commit, push, and open a PR into `main`.
6. **Tell the chat you pushed**, and what changed.
7. Merge when tests pass. If something on `main` breaks, revert it and say so in the chat.

You can pick the item you care about most ("I'm passionate about the calendar piece, I'll do that today"). Just claim it first.

## Repo layout

Keep everything in the repo so it doesn't turn into a messy shared drive:

```
docs/            planning docs (this folder): spec, priorities, architecture, handoffs
docs/class/      deliverable sheet, rubric, opportunities matrix, slides (add these)
calendeal/       the Python package
app/             the web app (to be built)
data/            sample deals + weekly snapshots
profiles/        demo user profiles
tests/           pytest
```

## Still to do as a team

- [ ] Upload the class deliverable sheet, rubric, and other Dropbox files into `docs/class/`.
- [ ] Fill in the **Agentic Opportunities Matrix** (`Agentic_Opportunities_Matrix_v2.xlsx` is still the blank template).
- [ ] Find real sources for the market stats (`docs/PRODUCT_SPEC.md`).
- [ ] Decide who owns evaluation (`docs/EVALUATION.md`).
- [ ] Run the decisions in `docs/DECISIONS.md` past the professor (Quinn), especially the data-source plan.
- [ ] Figma boards for the main screens (one teammate offered).
