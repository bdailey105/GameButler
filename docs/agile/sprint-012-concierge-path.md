# Sprint 012 — Rich Metadata Foundation

## Sprint Goal

Make the next path implementation-ready by starting with the most visible foundation: persist Steam art/descriptions and render richer cards.

## Committed Stories

| Story | Title | Status | Notes |
| --- | --- | --- | --- |
| E12-S1 | Add rich metadata fields to Game | Done | Backend/database/API slice complete. |
| E12-S2 | Save rich metadata during enrichment | Done | Uses existing `fetch_game_details` return shape. |
| E12-S3 | Render rich game cards | Done | Frontend visible payoff complete. |

## Acceptance Summary

By the end of this sprint:

- [x] `Game` persists `header_image` and `short_description`.
- [x] Enrichment writes these fields when Steam returns them.
- [x] Existing games without these fields still work.
- [x] Cards show image/description when available and degrade gracefully when missing.
- [x] Backend tests pass.
- [x] Frontend lint/build pass.
- [x] Docker compose config remains valid.

## Implementation Plan

Follow: [`../plans/2026-07-05-gamebutler-concierge-path.md`](../plans/2026-07-05-gamebutler-concierge-path.md)

## Verification Commands

Run targeted backend tests after backend changes:

```bash
.venv/bin/pytest tests/test_api.py tests/test_persistence.py tests/test_steam_client.py -v
```

Run frontend verification after UI changes:

```bash
cd frontend && npm run lint && npm run build
```

Run full local verification before closing sprint:

```bash
make verify
```

## Review Notes

Record observed outputs here when implementation completes.

```text
2026-07-05:
- .venv/bin/pytest tests/test_api.py tests/test_persistence.py tests/test_steam_client.py -v
  Result: 10 passed, 1 FastAPI/Starlette deprecation warning.
- cd frontend && npm run lint && npm run build
  Result: lint passed; Vite production build passed.
- make verify
  Result: 22 passed, 1 FastAPI/Starlette deprecation warning; frontend lint/build passed; docker compose config passed.
- E22 visual foundation follow-up:
  Result: Launcher nav, tokens, card states, empty/loading states, and responsive layout added. `make verify` passed with 22 tests, frontend lint/build, and docker compose config. Browser smoke checked desktop 1280px and mobile 390px with no horizontal overflow.
- E13 enrichment job progress follow-up:
  Result: durable `EnrichmentJob` model/endpoints, progress counters, and Library polling UI added. Targeted verification passed: 9 backend tests, frontend lint/build. Full `make verify` passed with 25 tests, frontend lint/build, and docker compose config.
- E14 recommendation scoring follow-up:
  Result: deterministic recommender scoring and reasons added; `/recommend` returns backward-compatible game fields plus `score` and `reasons`; Butler UI displays the match score and "Why this game" reasons. Full `make verify` passed with 29 tests, frontend lint/build, and docker compose config.
- E15 mood modes follow-up:
  Result: `/recommend` accepts validated mood presets; mood preferences affect deterministic scoring without overriding explicit filters; Butler UI exposes mood buttons and explanations include mood reasons. Full `make verify` passed with 34 tests, frontend lint/build, and docker compose config.
- E19 backup/restore follow-up:
  Result: `make backup` creates timestamped SQLite backups, `make restore BACKUP=...` restores with a pre-restore safety copy, backup files are ignored by git, and DEPLOY.md documents the restore/restart/health workflow. Verified with temp-db backup/restore checks, `make backup`, shell syntax checks, and full `make verify` passing with 34 tests, frontend lint/build, and docker compose config.
- E20 import safety follow-up:
  Result: `/upload/preview` reports total/new/existing/duplicate rows without writing; the Upload view requires confirmation before import; imports skip duplicate AppIDs, preserve enriched metadata on `Unknown` CSV fields, use OS temp files, and roll back failed writes. Full `make verify` passed with 37 tests, frontend lint/build, and docker compose config.
- E21 database migrations follow-up:
  Result: startup now records schema changes in `schema_migrations`; the rich metadata column upgrade is an idempotent migration; no migration dependency was added. Full `make verify` passed with 38 tests, frontend lint/build, and docker compose config.
- E16 queue ordering follow-up:
  Result: Up Next now persists `queue_position`, appends newly queued games, clears position when removed, backfills old queued games via migration, exposes `/games/queue` reorder, and provides move-earlier/move-later controls in the Backlog Up Next column. No drag-and-drop dependency was added. Full `make verify` passed with 42 tests, frontend lint/build, and docker compose config; browser smoke verified the Backlog board renders without horizontal overflow.
```

## Next Sprint Candidates

1. E17 — Bulk library editing.
2. E18 — Game detail drawer.
