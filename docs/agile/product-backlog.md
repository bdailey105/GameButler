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
