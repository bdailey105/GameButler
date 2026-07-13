# GameButler Agile Tracker

This folder tracks the next product path for GameButler as a local/home-LAN personal gaming concierge.

## Current Direction

GameButler has moved beyond the core MVP: Steam and external-library import, SQLite-backed library state, rich metadata, backlog curation, game journal, concierge feedback, tonight planning, continuation/finish guidance, and Docker/LAN deployment all exist on the current `Codex-update` branch. That branch is ahead of its remote and behind by one commit, so the previously planned E25–E30 capabilities are recorded as implemented-but-needing integration verification rather than silently treated as merged/released. The next path is to make the concierge more useful at the exact moment Bryan decides whether to resume, start, or set up a game.

## Current Planned Sequence

1. **E31 — Resume Me:** put the strongest continuation candidate, return context, next milestone, and launch action in one low-friction home-screen card.
2. **E32 — Gaming Context Profiles:** support reusable setup-aware recommendation profiles such as desk/controller, TV, Steam Deck, co-op, low-energy, and 30-minute sessions.
3. **E33 — Post-Session Outcomes:** capture an optional lightweight answer to whether a recommended session fit the desired mood and duration.
4. **E34 — Backlog Archaeology:** periodically resurface neglected games with transparent reasons, never guilt or opaque scoring.
5. **E35 — Curated Rotations:** owner-controlled seasonal or thematic shelves that act as an explicit recommendation signal.

`BACKLOG.md` retains the concise historical epic list. `product-backlog.md` is the implementation-ready source for E25–E30 reconciliation and the next E31–E35 opportunities; `roadmap.md` is the current phase/order summary.

## Documents

- [`roadmap.md`](roadmap.md) — phases and epic-level path.
- [`product-backlog.md`](product-backlog.md) — implementation-ready epics/stories with acceptance criteria.
- [`sprint-012-concierge-path.md`](sprint-012-concierge-path.md) — recommended next sprint.
- [`decision-log.md`](decision-log.md) — lightweight product/architecture decisions.
- [`story-template.md`](story-template.md) — copy/paste template for future stories.
- [`../GameButler — Design Document.pdf`](../GameButler%20%E2%80%94%20Design%20Document.pdf) — visual design handoff; selected direction is "The Launcher."
- [`../plans/2026-07-05-gamebutler-concierge-path.md`](../plans/2026-07-05-gamebutler-concierge-path.md) — detailed implementation plan for the first slice.
- [`../handoffs/2026-07-05-gamebutler-concierge-path.md`](../handoffs/2026-07-05-gamebutler-concierge-path.md) — compact handoff for another agent/developer.

## Status Legend

- **Backlog** — idea is captured but not ready to implement.
- **Ready** — story has acceptance criteria and verification commands.
- **In Progress** — implementation has started.
- **Review** — implementation complete, needs verification/review.
- **Done** — real verification was run and output recorded in the sprint/story.
- **Blocked** — cannot proceed without a decision or dependency.

## Working Agreement

- Keep work in thin vertical slices that leave the app runnable.
- Prefer deterministic code for recommendation decisions; optional local LLMs may explain or add personality later.
- Each story must include acceptance criteria and at least one verification command.
- Mark stories Done only after verification has actually run.
- Preserve the local/home-LAN deployment target unless explicitly changed.
- Keep SQLite backup/restore boring and reliable before adding riskier features.
- Use the Design Document's "The Launcher" direction for UI work: dark navy shell, blue primary action, compact dense cards, status colors, mobile states, and explicit empty/loading/skeleton states.

## Definition of Done

For implementation stories:

- [ ] Backend tests added or updated when backend behavior changes.
- [ ] Frontend lint/build passes when UI changes.
- [ ] API smoke check passes when endpoints change.
- [ ] Docker/LAN path remains documented and health-checkable.
- [ ] Docs/backlog updated to reflect shipped behavior.
