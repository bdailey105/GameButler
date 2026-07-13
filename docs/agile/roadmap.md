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
| E25 | Game Detail & Play Journal | Done | Current `Codex-update` branch adds private notes, ratings, milestones, and detail UI; confirm after branch integration. |

Success signal: Bryan can resume a game weeks later knowing where he left off and why he intended to return.

## Phase 5 — Adaptive Concierge

**Goal:** Improve Butler with reversible feedback and a concrete plan for the next session.

| Epic | Title | Status | Outcome |
| --- | --- | --- | --- |
| E26 | Concierge Feedback & Preference Learning | Done | Current branch records transparent accept/reject/defer feedback and applies explainable scoring adjustments. |
| E27 | Tonight Planner | Done | Current branch uses time, energy, and play-setting context for recommendations. |

Success signal: Bryan can ask what fits tonight and see a transparent explanation grounded in both current context and prior choices.

## Phase 6 — Intentional Progress & Curation

**Goal:** Make a large library easier to curate while making started games approachable again.

| Epic | Title | Status | Outcome |
| --- | --- | --- | --- |
| E28 | Continuation & Finish Ladder | Done | Current branch adds paused/return context and qualified continuation or finish guidance. |
| E29 | Bulk Library Curation | Done | Current branch adds bulk library actions and batch curation workflows. |

Success signal: Bryan can make a small, intentional curation pass and choose a meaningful continuation without turning the backlog into an obligation.

## Phase 7 — Unified Personal Library

**Goal:** Safely bring non-Steam ownership into GameButler before considering account-linking integrations.

| Epic | Title | Status | Outcome |
| --- | --- | --- | --- |
| E30 | Unified Library Import | Done | Current branch adds preview-first, source-aware external-library import without account credentials. |

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

## Phase 8 — Moment-of-Choice Concierge

**Goal:** Make GameButler useful in the few seconds when Bryan decides whether to resume, start, or set up a session.

| Epic | Title | Status | Outcome |
| --- | --- | --- | --- |
| E31 | Resume Me | Done | A home-screen continuation card joins return context, next milestone, approximate remaining time, and a launch action. |
| E32 | Gaming Context Profiles | Done | Reusable setup-aware profiles such as desk/controller, TV, Steam Deck, co-op, low-energy, and 30-minute sessions. |
| E33 | Post-Session Outcomes | In progress | Optional structured reflection on whether a recommendation fit the actual session. |
| E34 | Backlog Archaeology | Backlog | Periodically resurface neglected games with transparent reasons and an easy dismiss/defer path. |
| E35 | Curated Rotations | Backlog | Owner-controlled seasonal or thematic shelves that become explicit, reversible recommendation signals. |

Success signal: the app provides a credible next action with enough personal context to launch a game rather than reopen a browsing loop.