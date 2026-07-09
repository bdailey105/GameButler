# GameButler Roadmap

## Product Vision

GameButler is a personal gaming concierge for a large Steam library. It should reduce choice paralysis by combining library metadata, Bryan's backlog state, attention/mood preferences, and lightweight explanations into a clear answer to: **what should I play next?**

## Current Baseline

Shipped capabilities:

- FastAPI backend and React/Vite frontend.
- Steam CSV import with normalization.
- SQLite persistence for imported games, status, and attention level.
- Backlog statuses: Library, Up Next, Playing, Completed, Abandoned.
- Attention levels: Casual, Focused, Unset.
- Basic auto-tagging heuristics.
- Steam metadata enrichment for genres/tags.
- Steam art/descriptions persisted and rendered on richer game cards.
- Docker Compose local/home-LAN deployment.
- Backend test suite and frontend lint/build commands.

Known friction:

- Enrichment is fire-and-forget; no durable progress/job status.
- Recommendation is filter + random sample rather than scored/explained concierge behavior.
- Current UI is functional but not yet aligned to the selected "The Launcher" visual design direction.
- Library setup needs better bulk workflows and richer filters.
- Backup/restore is documented manually but not scripted.

## Phase 1 — Rich Metadata Foundation

**Goal:** Make imported games feel real and make enrichment trustworthy.

| Epic | Title | Status | Outcome |
| --- | --- | --- | --- |
| E12 | Persist Steam Art & Descriptions | Done | Game cards can display images/descriptions from Steam metadata. |
| E13 | Enrichment Job Progress | Done | User sees progress, success/failure counts, and can retry failed enrichment. |

Success signal: after clicking Enrich, Bryan can see progress and later browse rich game cards with art and descriptions.

## Phase 2 — Visual Design Foundation

**Goal:** Align the functional app to the selected Launcher design system before layering on more UI-heavy features.

Design source: `docs/GameButler — Design Document.pdf`.

| Epic | Title | Status | Outcome |
| --- | --- | --- | --- |
| E22 | Launcher Visual System | Done | App shell, game cards, empty/loading states, and mobile layout follow the selected design direction. |

Success signal: the app feels like the design handoff: dark navy shell, compact cards, clear status accents, responsive mobile screens, and polished empty/loading states.

## Phase 3 — Concierge Recommendations

**Goal:** Replace random filtered picks with explainable, mood-aware recommendations.

| Epic | Title | Status | Outcome |
| --- | --- | --- | --- |
| E14 | Recommendation Scoring | Done | `/recommend` returns a scored pick and explanation. |
| E15 | Mood Modes | Done | UI offers “Zone out,” “Story night,” “Short session,” and “Finish something.” |

Success signal: GameButler can say why a game is a good pick for tonight.

## Phase 4 — Personal Game Memory

**Goal:** Make every game retain Bryan's own context, not just provider metadata and raw Steam playtime.

| Epic | Title | Status | Outcome |
| --- | --- | --- | --- |
| E25 | Game Detail & Play Journal | Backlog | Each game has private notes, ratings, milestones, and an accessible detail drawer. |

Success signal: Bryan can resume a game weeks later knowing where he left off and why he intended to return.

## Phase 5 — Adaptive Concierge

**Goal:** Improve Butler with reversible feedback and a concrete plan for the next session.

| Epic | Title | Status | Outcome |
| --- | --- | --- | --- |
| E26 | Concierge Feedback & Preference Learning | Backlog | Butler learns from accepted, rejected, and deferred recommendations without opaque behavior. |
| E27 | Tonight Planner | Backlog | Recommendations account for time, energy, and play setting rather than only genre or total length. |

Success signal: Bryan can ask what fits tonight and see a transparent explanation grounded in both current context and prior choices.

## Phase 6 — Intentional Progress & Curation

**Goal:** Make a large library easier to curate while making started games approachable again.

| Epic | Title | Status | Outcome |
| --- | --- | --- | --- |
| E28 | Continuation & Finish Ladder | Backlog | Started or paused games surface as realistic continuation and finish options with qualified estimates. |
| E29 | Bulk Library Curation | Backlog | Selection, batch actions, and focused filter views eliminate one-card-at-a-time library cleanup. |

Success signal: Bryan can make a small, intentional curation pass and choose a meaningful continuation without turning the backlog into an obligation.

## Phase 7 — Unified Personal Library

**Goal:** Safely bring non-Steam ownership into GameButler before considering account-linking integrations.

| Epic | Title | Status | Outcome |
| --- | --- | --- | --- |
| E30 | Unified Library Import | Backlog | Source-aware, preview-first imports unify local records from Switch, PlayStation, Xbox, retro, and launcher exports. |

Success signal: GameButler can recommend across the games Bryan owns without storing third-party account credentials.

## Reliability Foundation

**Goal:** Keep the local/home-LAN deployment safe while the personal library becomes more valuable.

| Epic | Title | Status | Outcome |
| --- | --- | --- | --- |
| E19 | Backup/Restore Workflow | Done | `make backup` / `make restore` protect `data/gamebutler.db`. |
| E20 | Import Safety & Preview | Done | Steam imports are transactional, previewable, and collision-safe. |
| E21 | Database Migrations | Done | Schema changes are explicit and recoverable. |

Success signal: adding personal context and import sources does not risk losing curated library state.

## Recommended Sequence

1. E25 — Game Detail & Play Journal.
2. E26 — Concierge Feedback & Preference Learning.
3. E27 — Tonight Planner.
4. E28 — Continuation & Finish Ladder.
5. E29 — Bulk Library Curation.
6. E30 — Unified Library Import.

This sequence uses the existing rich production metadata as a foundation, then adds personal memory, explicit intent, and feedback before widening the library's scope.