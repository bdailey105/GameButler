# GameButler Agile Tracker

This folder tracks the next product path for GameButler as a local/home-LAN personal gaming concierge.

## Current Direction

GameButler already has the core MVP: Steam CSV import, SQLite-backed library state, backlog status management, attention tagging, basic Steam enrichment, and Docker/LAN deployment. The next path is to make it feel less like a CRUD backlog and more like a concierge that helps Bryan decide what to play.

## Current Planned Sequence

1. **E25 — Game Detail & Play Journal:** preserve private return context, notes, ratings, and milestones.
2. **E26 — Concierge Feedback & Preference Learning:** make recommendation acceptance and rejection actionable, explainable signals.
3. **E27 — Tonight Planner:** match a recommendation to available time, energy, and play setting.
4. **E28 — Continuation & Finish Ladder:** make started or paused games approachable with qualified estimates.
5. **E29 — Bulk Library Curation:** support intentional cleanup of a large library in batches.
6. **E30 — Unified Library Import:** safely import non-Steam ownership without account-linking dependencies.

`BACKLOG.md` retains the concise historical epic list. `product-backlog.md` is the implementation-ready source for the detailed acceptance criteria and verification commands for E25–E30.

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
