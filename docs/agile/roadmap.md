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

## Phase 4 — Backlog Operating System

**Goal:** Make the library and Up Next queue easy to curate at scale.

| Epic | Title | Status | Outcome |
| --- | --- | --- | --- |
| E16 | Queue Rules & Drag Ordering | Done | Up Next becomes an intentional queue, not just another status. |
| E17 | Bulk Library Editing | Backlog | Large libraries can be cleaned up quickly. |
| E18 | Game Detail Drawer | Backlog | Each game has a richer home for notes, metadata, and actions. |

Success signal: Bryan can manage hundreds of games without one-card-at-a-time friction.

## Phase 5 — Local Reliability

**Goal:** Make the home-LAN deployment safe to run long-term.

| Epic | Title | Status | Outcome |
| --- | --- | --- | --- |
| E19 | Backup/Restore Workflow | Done | `make backup` / `make restore` protect `data/gamebutler.db`. |
| E20 | Import Safety & Preview | Done | Uploads are transactional, previewable, and collision-safe. |
| E21 | Database Migrations | Done | Schema changes are explicit and recoverable. |

Success signal: adding metadata fields and jobs does not risk losing the local library.

## Recommended Sequence

1. E12 — Persist Steam art/descriptions. Done.
2. E22 — Launcher visual system foundation. Done.
3. E13 — Enrichment job progress. Done.
4. E14 — Recommendation scoring and explanation. Done.
5. E15 — Mood buttons. Done.
6. E19 — Backup/restore workflow. Done.
7. E20 — Import safety and preview. Done.
8. E21 — Database migrations. Done.
9. E16 — Queue rules and ordering. Done.

This sequence locks in the data foundation, applies the selected visual system before more UI-heavy work, then improves the core recommender and protects the local database.
