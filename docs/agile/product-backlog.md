# GameButler Product Backlog

## E12 — Persist Steam Art & Descriptions

**Goal:** Store and display rich Steam metadata already returned by `src/steam_client.py`.

### Story E12-S1 — Add rich metadata fields to Game

**As a** GameButler user, **I want** Steam images and descriptions persisted, **so that** the library survives restarts with rich card data.

**Status:** Done  
**Type:** AFK  
**Blocked by:** None

#### Acceptance Criteria

- [x] `Game` has nullable `header_image` and `short_description` fields.
- [x] API responses for `/games` and `/games/{app_id}` include the new fields.
- [x] Existing databases still start successfully.
- [x] Tests cover model/API serialization for the new fields.

#### Verification

```bash
.venv/bin/pytest tests/test_api.py tests/test_persistence.py -v
```

### Story E12-S2 — Save rich metadata during enrichment

**As a** GameButler user, **I want** enrichment to save art/descriptions, **so that** enriched games become visually useful.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E12-S1

#### Acceptance Criteria

- [x] `process_enrichment` writes `header_image` and `short_description` when Steam returns them.
- [x] Existing genre/tag enrichment behavior remains unchanged.
- [x] Missing Steam fields are stored as `None` or left unchanged rather than crashing.
- [x] Tests mock Steam responses and prove metadata is persisted.

#### Verification

```bash
.venv/bin/pytest tests/test_api.py tests/test_steam_client.py -v
```

### Story E12-S3 — Render rich game cards

**As a** GameButler user, **I want** cards to show art and short descriptions, **so that** browsing feels like a game library instead of a spreadsheet.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E12-S1

#### Acceptance Criteria

- [x] `GameCard` displays `header_image` when present.
- [x] `GameCard` displays a short description preview when present.
- [x] Cards still look acceptable for games without art/description.
- [x] Frontend lint and production build pass.

#### Verification

```bash
cd frontend && npm run lint && npm run build
```

## E13 — Enrichment Job Progress

**Goal:** Turn enrichment from fire-and-forget into visible durable progress.

### Story E13-S1 — Add enrichment job model and endpoints

**As a** GameButler user, **I want** enrichment to create a job record, **so that** progress can be tracked after the request returns.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E12-S1 recommended, not required

#### Acceptance Criteria

- [x] Add `EnrichmentJob` model with status, total, processed, succeeded, failed, timestamps, and error summary.
- [x] `POST /games/enrich` returns a `job_id`.
- [x] `GET /games/enrich/jobs/{job_id}` returns job progress.
- [x] `GET /games/enrich/jobs/current` returns the latest running or latest completed job.
- [x] Tests cover job lifecycle transitions.

#### Verification

```bash
.venv/bin/pytest tests/test_api.py -v
```

### Story E13-S2 — Update enrichment process to report progress

**As a** GameButler user, **I want** enrichment progress to update as games are processed, **so that** I know whether it is working.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E13-S1

#### Acceptance Criteria

- [x] Job `processed` increments per attempted game.
- [x] Job `succeeded` increments when metadata is saved.
- [x] Job `failed` increments for Steam/network failures.
- [x] Job status becomes `completed` or `failed` at the end.
- [x] Recommender sync still runs after successful enrichment.

#### Verification

```bash
.venv/bin/pytest tests/test_api.py tests/test_steam_client.py -v
```

### Story E13-S3 — Show enrichment progress in Library UI

**As a** GameButler user, **I want** a progress indicator after clicking Enrich, **so that** the UI does not feel stuck.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E13-S1, E13-S2

#### Acceptance Criteria

- [x] Enrich button starts a job and stores the returned `job_id`.
- [x] UI polls job progress while status is running.
- [x] UI shows processed/total and succeeded/failed counts.
- [x] UI stops polling when the job completes/fails.
- [x] Library refreshes after completion.

#### Verification

```bash
cd frontend && npm run lint && npm run build
```

## E14 — Recommendation Scoring & Explanation

**Goal:** Make GameButler recommend with reasons, not just random selection.

### Story E14-S1 — Introduce recommendation score model

**As a** GameButler user, **I want** recommendations ranked by fit, **so that** the result feels intentional.

**Status:** Done  
**Type:** AFK  
**Blocked by:** None

#### Acceptance Criteria

- [x] Add a deterministic scoring function in `src/recommender.py` or a new `src/recommendation_service.py`.
- [x] Completed and abandoned games remain excluded by default.
- [x] Matching attention, Up Next status, unplayed/started state, and length constraints influence score.
- [x] Tests cover scoring order and exclusion rules.
- [x] Randomness is limited to tie-breaking or explicit temperature behavior.

#### Verification

```bash
.venv/bin/pytest tests/test_recommender.py -v
```

### Story E14-S2 — Return explanation from `/recommend`

**As a** GameButler user, **I want** to know why a game was recommended, **so that** I can trust or reject the suggestion quickly.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E14-S1

#### Acceptance Criteria

- [x] Recommendation response includes `score` and `reasons` fields.
- [x] Explanations are deterministic strings from scoring signals.
- [x] Existing recommendation fields remain backward compatible.
- [x] UI displays the explanation under the recommended game.

#### Verification

```bash
.venv/bin/pytest tests/test_api.py tests/test_recommender.py -v
cd frontend && npm run lint && npm run build
```

## E15 — Mood Modes

**Goal:** Let Bryan ask in human terms instead of metadata terms.

### Story E15-S1 — Backend mood presets

**As a** GameButler user, **I want** mood presets like “zone out” and “short session,” **so that** I can ask the concierge naturally.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E14-S1

#### Acceptance Criteria

- [x] `/recommend` accepts a `mood` query param.
- [x] Supported moods: `zone_out`, `story_night`, `short_session`, `finish_something`, `surprise_me`.
- [x] Moods map to scoring/filter preferences without overriding explicit user filters.
- [x] Invalid moods return validation errors.

#### Verification

```bash
.venv/bin/pytest tests/test_api.py tests/test_recommender.py -v
```

### Story E15-S2 — Mood buttons in Concierge UI

**As a** GameButler user, **I want** one-click mood buttons, **so that** I do not have to type genres/tags when I am undecided.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E15-S1

#### Acceptance Criteria

- [x] Concierge view has mood buttons for each supported mood.
- [x] Selecting a mood passes `mood` to `getRecommendation`.
- [x] Explicit filters remain visible and usable.
- [x] Recommendation explanation makes the mood effect clear.

#### Verification

```bash
cd frontend && npm run lint && npm run build
```

## E16 — Queue Rules & Drag Ordering

**Goal:** Make Up Next behave like an intentional play queue instead of a loose status bucket.

### Story E16-S1 — Persist Up Next order

**As a** GameButler user, **I want** queued games to keep their order, **so that** my next few sessions stay intentional across refreshes and restarts.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E21

#### Acceptance Criteria

- [x] Games have an optional `queue_position`.
- [x] Moving a game into Up Next appends it to the end of the queue.
- [x] Moving a game out of Up Next clears its queue position.
- [x] Existing Up Next games are backfilled with deterministic positions during migration.
- [x] Up Next lists are returned and displayed in queue order.

#### Verification

```bash
.venv/bin/pytest tests/test_api.py tests/test_persistence.py -q
make verify
```

### Story E16-S2 — Reorder Up Next

**As a** GameButler user, **I want** to move queued games earlier or later, **so that** the queue reflects what I actually want to play next.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E16-S1

#### Acceptance Criteria

- [x] Backend exposes a reorder endpoint for queued AppIDs.
- [x] Reorder rejects duplicate IDs, games that are not currently queued, and partial queue payloads.
- [x] Backlog Up Next cards expose move-earlier/move-later controls.
- [x] No drag-and-drop dependency is added.

#### Verification

```bash
.venv/bin/pytest tests/test_api.py -q
cd frontend && npm run lint && npm run build
```

## E19 — Backup/Restore Workflow

**Goal:** Protect the local SQLite database before the app accumulates more personal curation.

### Story E19-S1 — Add `make backup`

**As a** GameButler operator, **I want** a one-command backup, **so that** I can safely preserve my curated library.

**Status:** Done  
**Type:** AFK  
**Blocked by:** None

#### Acceptance Criteria

- [x] `scripts/backup-db.sh` creates timestamped copies under `backups/`.
- [x] `make backup` runs the script.
- [x] Script fails clearly if `data/gamebutler.db` is missing.
- [x] Backup files are ignored by git.
- [x] DEPLOY.md documents backup usage.

#### Verification

```bash
make backup
```

### Story E19-S2 — Add `make restore`

**As a** GameButler operator, **I want** a deliberate restore command, **so that** I can recover from a bad import or broken migration.

**Status:** Done  
**Type:** HITL  
**Blocked by:** E19-S1

#### Acceptance Criteria

- [x] `scripts/restore-db.sh` restores a specified backup path.
- [x] Restore refuses to run without an explicit backup argument.
- [x] Restore creates a pre-restore safety copy of the current DB.
- [x] `make restore BACKUP=...` is documented.
- [x] Restore workflow includes `make restart && make health` after restoring.

#### Verification

```bash
make backup
make restore BACKUP=<path-to-backup>
make health
```

## E20 — Import Safety & Preview

**Goal:** Make CSV uploads safe enough to trust with a growing local library.

### Story E20-S1 — Preview imports before writing

**As a** GameButler user, **I want** to preview what a CSV upload will change, **so that** I can catch wrong files or duplicate exports before touching my library.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E19

#### Acceptance Criteria

- [x] Upload view previews total rows, new games, existing games, and duplicate rows before import.
- [x] Preview uses a backend endpoint that parses the CSV without writing to the database.
- [x] Duplicate AppIDs are surfaced in the preview.
- [x] The user explicitly confirms before importing the selected file.

#### Verification

```bash
.venv/bin/pytest tests/test_api.py -q
cd frontend && npm run lint && npm run build
```

### Story E20-S2 — Make imports transactional and collision-safe

**As a** GameButler operator, **I want** failed or duplicate imports to be safe, **so that** one bad CSV row does not corrupt my library.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E20-S1

#### Acceptance Criteria

- [x] Upload writes are committed only after the import loop completes.
- [x] Failed imports explicitly roll back pending database writes.
- [x] Duplicate AppIDs in one CSV are skipped after the first row.
- [x] Existing enriched metadata is preserved when an upload row only has `Unknown` genre/tags.
- [x] Temporary upload files use unique OS temp paths instead of repo-local filenames.

#### Verification

```bash
.venv/bin/pytest tests/test_api.py -q
make verify
```

## E21 — Database Migrations

**Goal:** Make schema changes explicit and recoverable before the local library accumulates more personal curation.

### Story E21-S1 — Add a minimal migration ledger

**As a** GameButler operator, **I want** startup schema changes to be recorded, **so that** database upgrades are visible instead of hidden in one-off helpers.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E19

#### Acceptance Criteria

- [x] Startup creates a `schema_migrations` table.
- [x] Each migration has a stable id and runs at most once.
- [x] Existing ad hoc rich metadata column upgrade is represented as a migration.
- [x] Running migrations repeatedly is safe.
- [x] No new dependency is added for migration plumbing.

#### Verification

```bash
.venv/bin/pytest tests/test_persistence.py -q
make verify
```

## E22 — Launcher Visual System

**Goal:** Bring the current React app into alignment with `docs/GameButler — Design Document.pdf`, using the selected "The Launcher" direction as the visual foundation.

### Story E22-S1 — Add Launcher design tokens

**As a** GameButler user, **I want** the app to have a coherent visual system, **so that** every screen feels like one focused concierge product.

**Status:** Done  
**Type:** AFK  
**Blocked by:** None

#### Acceptance Criteria

- [x] Global CSS tokens cover the design document's background, card, overlay, brand, status, text, border, spacing, and radius values.
- [x] Existing colors are replaced with token references where practical.
- [x] Focus states use the documented blue focus treatment.
- [x] No new dependency is added for tokens/theme plumbing.

#### Verification

```bash
cd frontend && npm run lint && npm run build
```

### Story E22-S2 — Refresh app shell and navigation

**As a** GameButler user, **I want** the app shell to match the Launcher design, **so that** Dashboard, Library, Backlog, and Butler feel like a deliberate desktop app.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E22-S1

#### Acceptance Criteria

- [x] Top navigation uses the Launcher dark navy shell and blue active tab treatment.
- [x] Navigation labels align to the design document: Dashboard, Library, Backlog, Butler, Upload/Settings as needed.
- [x] Library count/status chip appears when game counts are available.
- [x] Layout remains usable on desktop and mobile widths.

#### Verification

```bash
cd frontend && npm run lint && npm run build
```

### Story E22-S3 — Convert game cards to Launcher card system

**As a** GameButler user, **I want** game cards to use art, badges, and status accents consistently, **so that** rich metadata is easy to scan.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E12, E22-S1

#### Acceptance Criteria

- [x] Cards use the design document's compact dark card style with status border/accent coding.
- [x] `header_image` is displayed when present, with a styled art placeholder when missing.
- [x] `short_description`, genre/tag badges, status, attention, and primary actions fit without clipping.
- [x] Empty, loading, hover, and pressed states are represented for card lists.

#### Verification

```bash
cd frontend && npm run lint && npm run build
```

### Story E22-S4 — Add mobile and empty-state polish

**As a** GameButler user, **I want** the app to work cleanly on phone-sized screens and empty libraries, **so that** setup and casual use feel intentional.

**Status:** Done  
**Type:** AFK  
**Blocked by:** E22-S1

#### Acceptance Criteria

- [x] Mobile layout follows the design document's bottom-tab pattern or an equivalent compact navigation.
- [x] Dashboard, Library, Butler, and Backlog have explicit empty states.
- [x] Loading/skeleton states exist for library fetching and enrichment/recommendation work.
- [x] No text overlaps, clips, or shifts unexpectedly at mobile widths.

#### Verification

```bash
cd frontend && npm run lint && npm run build
```

## E25 — Game Detail & Play Journal

**Goal:** Give each game a private home for the personal context that metadata and Steam playtime cannot capture.

### Story E25-S1 — Persist personal game context

**As a** GameButler user, **I want** to record my own notes, rating, and play milestones for a game, **so that** I can resume it without reconstructing context from memory.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** None

#### Acceptance Criteria

- [ ] Games can store an optional personal rating, started/completed dates, and a concise current-state note.
- [ ] A game can have append-only journal entries with timestamps; existing Steam-derived `PlayEvent` records remain unchanged.
- [ ] Empty personal fields do not change existing game-card or recommendation behavior.
- [ ] A schema migration and persistence tests cover new fields and journal records.

#### Verification

```bash
env -u PYTHONPATH .venv/bin/pytest tests/test_persistence.py tests/test_api.py -q
```

### Story E25-S2 — Expose game detail and journal APIs

**As a** GameButler client, **I want** read/write endpoints for personal game context and journal entries, **so that** the frontend can show a complete game history without client-side data hacks.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E25-S1

#### Acceptance Criteria

- [ ] `GET /games/{id}` returns a game with personal context and chronologically ordered journal entries.
- [ ] Validated endpoints create, edit, and delete only a user's own journal entries for an existing game.
- [ ] Invalid dates, ratings outside the documented range, blank entries, and missing game IDs return clear errors.
- [ ] API tests cover empty, populated, and validation cases.

#### Verification

```bash
env -u PYTHONPATH .venv/bin/pytest tests/test_api.py -q
```

### Story E25-S3 — Add a Game Detail Drawer

**As a** GameButler user, **I want** a detail drawer from any game card, **so that** I can view metadata, play history, and personal notes without losing my place in the library.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E25-S2, E22

#### Acceptance Criteria

- [ ] A card action opens an accessible drawer with art, metadata, status actions, personal context, and journal timeline.
- [ ] The drawer supports adding a note and editing personal context with explicit saved/error feedback.
- [ ] Keyboard focus is trapped while open and returns to the originating card when closed.
- [ ] Empty and loading states are provided for games without notes or enriched metadata.

#### Verification

```bash
cd frontend && npm run lint && npm run build
```

## E26 — Concierge Feedback & Preference Learning

**Goal:** Let GameButler learn from recommendation decisions while keeping every influence inspectable and reversible.

### Story E26-S1 — Record recommendation decisions

**As a** GameButler user, **I want** to record why I accepted or rejected a recommendation, **so that** future picks reflect my actual preferences rather than only static metadata.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E14

#### Acceptance Criteria

- [ ] A recommendation decision stores the game, recommendation context, decision type, optional reason, and timestamp.
- [ ] Supported rejection reasons include not in the mood, too long, too demanding, already bounced off it, and defer for now.
- [ ] Decision creation validates the game and enumerated reason values without mutating game status unless an explicit action requests it.
- [ ] Persistence and API tests cover accepted, rejected, deferred, and invalid decisions.

#### Verification

```bash
env -u PYTHONPATH .venv/bin/pytest tests/test_api.py tests/test_persistence.py -q
```

### Story E26-S2 — Add recommendation feedback controls

**As a** GameButler user, **I want** to give quick feedback directly on Butler picks, **so that** I can reject an unhelpful answer in one step.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E26-S1

#### Acceptance Criteria

- [ ] The main recommendation and alternates offer Play now, Up Next, Not tonight, and More/Less like this controls.
- [ ] Rejecting a game can optionally capture one predefined reason without requiring free text.
- [ ] Feedback shows a durable confirmation and does not hide the current recommendation unexpectedly.
- [ ] Controls remain usable by keyboard and announce result state to assistive technology.

#### Verification

```bash
cd frontend && npm run lint && npm run build
```

### Story E26-S3 — Apply transparent preference adjustments

**As a** GameButler user, **I want** recommendation explanations to show how my feedback affected a pick, **so that** preference learning remains trustworthy and under my control.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E26-S1

#### Acceptance Criteria

- [ ] Scoring applies deterministic, documented adjustments from recent recommendation decisions.
- [ ] A deferred game is temporarily deprioritized rather than permanently hidden.
- [ ] Recommendation reasons distinguish personal-feedback signals from mood, queue, and metadata signals.
- [ ] A preference-history endpoint or settings view lets the user inspect and clear learned signals.
- [ ] Regression tests pin scoring behavior and reset behavior.

#### Verification

```bash
env -u PYTHONPATH .venv/bin/pytest tests/test_recommender.py tests/test_api.py -q
```

## E27 — Tonight Planner

**Goal:** Turn “what should I play?” into a recommendation that respects the time, energy, and setting of the next session.

### Story E27-S1 — Add session-planning inputs to the recommender

**As a** GameButler user, **I want** to describe tonight's available time, energy, and setting, **so that** Butler can distinguish a short game from a game that fits this particular session.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E14, E15

#### Acceptance Criteria

- [ ] `/recommend` accepts optional validated session inputs for available minutes, energy level, and play context.
- [ ] Explicit filters continue to take precedence over session-planning defaults.
- [ ] The response explains which session inputs influenced the score.
- [ ] Unknown metadata lowers confidence rather than falsely claiming a game fits the session.
- [ ] Recommender/API tests cover valid combinations, invalid inputs, and explicit-filter precedence.

#### Verification

```bash
env -u PYTHONPATH .venv/bin/pytest tests/test_recommender.py tests/test_api.py -q
```

### Story E27-S2 — Build the Tonight Planner UI

**As a** GameButler user, **I want** a one-screen session planner, **so that** I can ask for a useful recommendation without configuring raw metadata filters.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E27-S1

#### Acceptance Criteria

- [ ] Butler offers quick choices for 15/30/60/90+ minutes, energy, and context such as desk, couch, handheld, or podcast-friendly.
- [ ] The planner keeps advanced genre/tag filters available but visually secondary.
- [ ] Chosen inputs remain visible in the recommendation explanation and can be reset in one action.
- [ ] Mobile layout supports the entire flow without horizontal scrolling or obscured controls.

#### Verification

```bash
cd frontend && npm run lint && npm run build
```

### Story E27-S3 — Add game session-suitability overrides

**As a** GameButler user, **I want** to mark a game as good for bursts, controller-only, or podcast-friendly, **so that** personal experience can correct generic metadata.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E25-S1, E27-S1

#### Acceptance Criteria

- [ ] Game detail supports optional, user-controlled session-suitability tags.
- [ ] Planner scoring uses these tags as explicit, explainable bonuses only when they match the chosen context.
- [ ] Untagged games remain eligible and receive no invented suitability claims.
- [ ] Persistence, API, and scoring tests cover manual overrides and unset tags.

#### Verification

```bash
env -u PYTHONPATH .venv/bin/pytest tests/test_persistence.py tests/test_api.py tests/test_recommender.py -q
```

## E28 — Continuation & Finish Ladder

**Goal:** Help the user make intentional progress on started games without pretending that playtime is exact story completion.

### Story E28-S1 — Add a paused state and continuation context

**As a** GameButler user, **I want** to pause a game with an optional return note, **so that** I can defer it without confusing it with an abandoned or never-started game.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E25-S1

#### Acceptance Criteria

- [ ] Game status supports a paused state and status transitions are recorded in `PlayEvent`.
- [ ] Paused games are excluded from default recommendations but can be explicitly requested by continuation-oriented planning.
- [ ] A paused game can record an optional “return when…” note without requiring a journal entry.
- [ ] Migration, API, and recommender tests cover status transitions and default exclusions.

#### Verification

```bash
env -u PYTHONPATH .venv/bin/pytest tests/test_persistence.py tests/test_api.py tests/test_recommender.py -q
```

### Story E28-S2 — Return estimated remaining time with confidence

**As a** GameButler user, **I want** a clearly qualified estimate of what remains for a started game, **so that** I can choose between a continuation and a fresh start responsibly.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E28-S1, E19

#### Acceptance Criteria

- [ ] The API can return an estimated remaining duration for eligible games based on available time-to-beat and playtime.
- [ ] Each estimate includes a confidence/status label that makes clear it is metadata-derived rather than actual completion tracking.
- [ ] Missing, zero, or implausible source values result in an unavailable estimate instead of a misleading number.
- [ ] Tests cover estimates, missing metadata, and games whose playtime exceeds the source duration.

#### Verification

```bash
env -u PYTHONPATH .venv/bin/pytest tests/test_api.py tests/test_recommender.py -q
```

### Story E28-S3 — Present a continuation and finish ladder

**As a** GameButler user, **I want** ranked continuation options such as “15 minutes,” “one session,” and “this week,” **so that** progress feels approachable rather than like another backlog obligation.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E27-S1, E28-S2

#### Acceptance Criteria

- [ ] Butler can return ranked continuation candidates for short, medium, and finish-oriented horizons.
- [ ] Results prioritize active/queued games and clearly explain status, recent activity, and estimate signals.
- [ ] The UI labels estimates as approximate and provides an empty state when no trustworthy candidates exist.
- [ ] Regression tests pin default ranking and horizon-specific behavior.

#### Verification

```bash
env -u PYTHONPATH .venv/bin/pytest tests/test_recommender.py tests/test_api.py -q
cd frontend && npm run lint && npm run build
```

## E29 — Bulk Library Curation

**Goal:** Let a large personal library be curated in batches, so recommendation quality improves without one-card-at-a-time work.

### Story E29-S1 — Add atomic bulk game updates

**As a** GameButler user, **I want** to update selected games together, **so that** I can apply consistent backlog and attention decisions efficiently.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E21

#### Acceptance Criteria

- [ ] A bulk endpoint applies supported status, attention, and session-suitability changes to a supplied list of game IDs in one transaction.
- [ ] The endpoint rejects empty selections, missing IDs, invalid values, and partial failures without making a partial update.
- [ ] Queue ordering rules remain correct when bulk actions move games into or out of Up Next.
- [ ] API and persistence tests cover success, rollback, and queue edge cases.

#### Verification

```bash
env -u PYTHONPATH .venv/bin/pytest tests/test_api.py tests/test_persistence.py -q
```

### Story E29-S2 — Add multi-select library workflows

**As a** GameButler user, **I want** to select and update multiple library games from the list view, **so that** I can clean up a large backlog quickly.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E29-S1

#### Acceptance Criteria

- [ ] Library cards support keyboard-accessible multi-select with a clear selected-count indicator.
- [ ] A bulk-action bar can set status, attention, and session-suitability tags for the current selection.
- [ ] Destructive or high-impact actions require explicit confirmation and report affected-count results.
- [ ] Selection is cleared or reconciled predictably after filters, refreshes, and successful actions.

#### Verification

```bash
cd frontend && npm run lint && npm run build
```

### Story E29-S3 — Add curation views and saved filters

**As a** GameButler user, **I want** focused views for neglected or uncategorized games, **so that** I can make small, intentional cleanup passes.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E29-S2

#### Acceptance Criteria

- [ ] Library provides filter presets for untagged attention, never played, started-but-not-active, and deferred games.
- [ ] A user can save and reuse a named local filter combination without sharing data externally.
- [ ] Filter views show counts and explicit empty states.
- [ ] API and UI tests cover preset query behavior and saved-filter validation.

#### Verification

```bash
env -u PYTHONPATH .venv/bin/pytest tests/test_api.py -q
cd frontend && npm run lint && npm run build
```

## E30 — Unified Library Import

**Goal:** Bring non-Steam ownership into GameButler through reliable, import-first workflows before considering fragile account-linking integrations.

### Story E30-S1 — Add source-aware external game identity

**As a** GameButler user, **I want** imported non-Steam games to retain their platform and source identity, **so that** repeated imports update the right record instead of creating duplicates.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** AFK
**Blocked by:** E16, E21

#### Acceptance Criteria

- [ ] Games can persist an optional library source and source-specific external ID in addition to the existing platform.
- [ ] Database uniqueness rules prevent duplicate records for the same source/external-ID pair while preserving manual games without a source ID.
- [ ] Existing Steam and manually created games migrate without loss or identity collisions.
- [ ] Migration and persistence tests cover duplicate prevention and backward compatibility.

#### Verification

```bash
env -u PYTHONPATH .venv/bin/pytest tests/test_persistence.py tests/test_api.py -q
```

### Story E30-S2 — Preview and import a normalized external library file

**As a** GameButler user, **I want** to preview a non-Steam library import before it writes, **so that** I can safely bring in Switch, PlayStation, Xbox, retro, or launcher-exported games.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** HITL
**Blocked by:** E30-S1, E20

#### Acceptance Criteria

- [ ] The importer accepts a documented normalized CSV format with title, platform, source, and optional external ID/metadata columns.
- [ ] Preview reports new, updated, duplicate, skipped, and invalid rows before confirmation.
- [ ] Import preserves existing personal status, notes, ratings, and manual metadata unless the user explicitly elects to replace a field.
- [ ] Invalid headers, duplicate source identities, and unsupported platforms return actionable validation errors.

#### Verification

```bash
env -u PYTHONPATH .venv/bin/pytest tests/test_data_loader.py tests/test_api.py -q
```

### Story E30-S3 — Add unified-library import UI and source filters

**As a** GameButler user, **I want** a guided import flow and source filters, **so that** games from every platform remain understandable in one concierge library.

**Status:** Done (2026-07-13 integration gate: rebase onto origin clean, 175 backend tests pass, frontend lint+build pass)
**Type:** HITL
**Blocked by:** E30-S2

#### Acceptance Criteria

- [x] Upload guides the user through file selection, preview, explicit confirmation, and results for external-library imports.
- [x] Library and game detail surfaces show platform/source identity without cluttering Steam-only workflows.
- [x] Source and platform filters can be combined with existing status, attention, and search filters.
- [x] The UI explains that imports are local and account credentials are not requested or stored.

#### Verification to record after integration

```bash
cd frontend && npm run lint && npm run build
```

## Reconciliation — E25 through E30

**Status:** Done. Integration gate passed 2026-07-13: rebased onto origin/Codex-update (picked up auto-enrich fix 4ccbaab), full backend suite 175 passed, frontend eslint clean, vite build clean.

Git commits `6a4f5b1` through `a284f1b` implement E25–E30 and include corresponding backend/frontend test changes. The branch is ahead of its remote and behind by one commit, so these stories must not be marked Done until their integration/rebase decision is made and the current backend, frontend, and Docker/LAN quality gates are recorded.

## E31 — Resume Me

**Status:** Done (2026-07-13: GET /recommend/resume + dashboard Resume card; 184 backend tests, lint+build clean)

**Goal:** Put the best continuation decision on the home surface so resuming a game takes less effort than browsing the library.

### Story E31-S1 — Build a deterministic resume candidate

**Acceptance Criteria**

- [x] Backend ranks paused/playing/Up Next games using existing return notes, recent activity, queue position, and qualified remaining-time data.
- [x] The response includes explicit reasons and never invents progress or context when data is missing.
- [x] Tests cover tie-breaking, missing notes, excluded statuses, and approximate estimates.

### Story E31-S2 — Render a launchable resume card

**Acceptance Criteria**

- [x] Dashboard renders one clear continuation card with return note, next milestone, estimate caveat, and available launcher link.
- [x] Missing Steam/launcher identity disables launch gracefully without hiding the game context.
- [x] Mobile and desktop states remain aligned to the Launcher design system.

## E32 — Gaming Context Profiles

**Status:** Done (2026-07-13: ContextProfile CRUD, profile-aware /recommend with visible influence, planner profile chips; 193 backend tests, lint+build clean, CRUD+recommend smoke-tested)

Persist reusable, user-controlled profiles such as desk/controller, TV, Steam Deck, co-op, low-energy, or 30-minute sessions. Profiles apply explainable filtering/bonuses; they do not infer hardware or preferences silently.

## E33 — Post-Session Outcomes

**Status:** Done (2026-07-13: SessionOutcome + pending/record endpoints, concierge reflection card; 203 backend tests, lint+build clean, endpoints smoke-tested)

After a chosen session, offer an optional one-question reflection: whether the game fit the intended mood, time, and setting. The signal supplements—not replaces—existing explicit feedback.

## E34 — Backlog Archaeology

**Status:** In progress

Periodically surface neglected games using transparent facts such as last-seen date, playtime, and similarity to a recently enjoyed game. Every surfaced game supports dismiss/defer; no guilt-based streaks or opaque engagement metrics.

## E35 — Curated Rotations

**Status:** Backlog

Allow owner-controlled seasonal or thematic shelves—such as comfort games, Halloween, or before-the-sequel—to act as visible, reversible recommendation signals. A rotation is curated data, not a hidden algorithmic preference.
