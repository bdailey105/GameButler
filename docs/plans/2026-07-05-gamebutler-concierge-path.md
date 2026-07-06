# GameButler Concierge Path Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Implement the first path slice: persist Steam art/descriptions and display richer game cards.

**Architecture:** Keep SQLite as the source of truth. Extend the existing `Game` model with nullable rich metadata fields, save fields during the existing enrichment process, then render the fields in the existing `GameCard` component with graceful fallbacks.

**Visual Direction:** `docs/GameButler — Design Document.pdf` is the UI/UX source of truth. The selected direction is "The Launcher": dark navy app shell, blue primary actions, compact game cards, status accents, responsive mobile screens, and explicit empty/loading/skeleton states.

**Tech Stack:** Python, FastAPI, SQLModel, pytest, React, Vite, npm lint/build, Docker Compose.

---

## Current Code Seams

- Backend API: `src/api.py`
- Data model: `src/models.py`
- Steam metadata client: `src/steam_client.py`
- Persistence/session helpers: `src/database.py`
- Frontend API wrapper: `frontend/src/api.js`
- Main UI/cards: `frontend/src/App.jsx`
- Styles: `frontend/src/App.css`
- Backend tests: `tests/test_api.py`, `tests/test_persistence.py`, `tests/test_steam_client.py`

## Task 1 — Add rich metadata fields to `Game`

**Objective:** Allow each game to persist optional Steam image and description fields.

**Files:**

- Modify: `src/models.py`
- Test: `tests/test_persistence.py` or `tests/test_api.py`

**Steps:**

1. Add nullable fields to `GameBase`:
   - `header_image: Optional[str] = None`
   - `short_description: Optional[str] = None`
2. Add/update a test that creates a `Game` with those fields and reads it back through SQLModel.
3. Run targeted persistence/API tests.
4. If an existing checked-in SQLite database does not pick up new columns automatically, add a minimal migration helper before app startup. Do not silently delete the DB.

**Verification:**

```bash
.venv/bin/pytest tests/test_persistence.py tests/test_api.py -v
```

## Task 2 — Include metadata when seeding/importing games

**Objective:** Ensure sample/import flows initialize the new fields safely.

**Files:**

- Modify: `src/api.py`
- Test: `tests/test_api.py`

**Steps:**

1. When constructing `Game(...)` from sample data or uploads, pass `header_image=None` and `short_description=None` only if needed for clarity.
2. Confirm upload update logic does not overwrite existing rich metadata with missing CSV data.
3. Add or update tests around upload/update preservation if coverage exists.

**Verification:**

```bash
.venv/bin/pytest tests/test_api.py -v
```

## Task 3 — Save rich metadata during enrichment

**Objective:** Persist Steam fields already returned by `fetch_game_details`.

**Files:**

- Modify: `src/api.py`
- Test: `tests/test_api.py` and/or `tests/test_steam_client.py`

**Steps:**

1. In `process_enrichment`, after `details = await fetch_game_details(game.id)`, set:
   - `game.header_image = details.get("header_image") or game.header_image`
   - `game.short_description = details.get("short_description") or game.short_description`
2. Preserve current genre/category behavior.
3. Add mocked enrichment test so no real Steam network call is required.
4. Ensure failures still skip/continue as today.

**Verification:**

```bash
.venv/bin/pytest tests/test_api.py tests/test_steam_client.py -v
```

## Task 4 — Render rich metadata in cards

**Objective:** Make enriched games visibly richer in the React UI.

**Files:**

- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/App.css`

**Steps:**

1. In `GameCard`, render `game.header_image` as a card image when present.
2. Render `game.short_description` as a short preview when present.
3. Add fallback styling for cards without images.
4. Keep current status and attention controls unchanged.
5. Avoid changing `frontend/src/api.js` unless response mapping requires it; Axios already returns all fields.

**Verification:**

```bash
cd frontend && npm run lint && npm run build
```

## Task 5 — Run full verification and update sprint evidence

**Objective:** Prove the path slice is safe and record the result.

**Files:**

- Modify: `docs/agile/sprint-012-concierge-path.md`

**Steps:**

1. Run the full verification command:

   ```bash
   make verify
   ```

2. Paste or summarize observed output in the sprint review notes.
3. Update story statuses in `docs/agile/product-backlog.md` if stories are completed.
4. Commit the implementation and docs as a coherent sprint checkpoint.

**Verification:**

```bash
make verify
git status --short
```

## Follow-up Plan

The concierge-path slice is complete through the local reliability follow-up, migration ledger, and queue ordering.

Next roadmap candidates:

1. E17 — Bulk library editing.
2. E18 — Game detail drawer.

Do not add an LLM butler voice until deterministic recommendation reasons exist.
