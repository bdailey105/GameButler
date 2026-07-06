# GameButler Concierge Path Handoff — 2026-07-05

## Mission

Continue GameButler along the next product path: turn the current local MVP into a richer personal gaming concierge.

## Current Product State

GameButler already supports:

- Steam CSV import.
- SQLite persistence.
- FastAPI backend and React/Vite frontend.
- Library, Up Next, Playing, Completed, and Abandoned statuses.
- Casual/Focused/Unset attention levels.
- Basic auto-tagging.
- Steam metadata enrichment for genre/tag fields.
- Docker Compose local/home-LAN deployment.

## Recommended Path

1. Persist Steam art/descriptions and render rich cards.
2. Add durable enrichment job progress.
3. Add recommendation scoring and deterministic explanations.
4. Add mood buttons in the Concierge view.
5. Add backup/restore commands for SQLite safety.

## New Planning Docs

- Agile index: `docs/agile/README.md`
- Roadmap: `docs/agile/roadmap.md`
- Backlog: `docs/agile/product-backlog.md`
- Current sprint: `docs/agile/sprint-012-concierge-path.md`
- Decisions: `docs/agile/decision-log.md`
- Implementation plan: `docs/plans/2026-07-05-gamebutler-concierge-path.md`

## First Implementation Slice

Start with E12:

- Add `header_image` and `short_description` to `src/models.py`.
- Persist those fields during `process_enrichment` in `src/api.py`.
- Render fields in `frontend/src/App.jsx` / `frontend/src/App.css`.
- Verify with backend pytest plus frontend lint/build.

## Important Decisions

- Keep local/home-LAN as the target.
- Keep recommender decisions deterministic.
- Optional LLM features can explain/add personality later but should not own ranking or persistence.
- Avoid expanding status enums until a concrete workflow requires it.

## Verification Commands

```bash
.venv/bin/pytest tests/test_api.py tests/test_persistence.py tests/test_steam_client.py -v
cd frontend && npm run lint && npm run build
make verify
```

## Workspace Note

At planning time, the repo already had unrelated modified/untracked files. Preserve user work; do not reset or clean without explicit instruction.
