# Story 7.1: Persistence Layer Setup (SQLite)

**Epic:** Epic 7: Backlog Management & Attention Tracking
**Priority:** High
**Status:** Ready for Review

## Description
Currently, GameButler loads data from a CSV file into memory (Pandas DataFrame). This means any changes to data (like setting a status) are lost on restart. We need to implement a persistent SQLite database using **SQLModel** (which combines SQLAlchemy and Pydantic) to store game data, allowing for stateful management.

## Technical Tasks
- [x] **Install SQLModel**: Add `sqlmodel` to `requirements.txt`.
- [x] **Define Models**: Create `src/models.py`.
- [x] **Database Initialization**: Create `src/database.py`.
- [x] **Migration Logic**: Update `src/data_loader.py` or `src/api.py`.
- [x] **Refactor Recommender**: Update `src/recommender.py`.

## Acceptance Criteria
- [x] `sqlmodel` is installed.
- [x] `gamebutler.db` file is created in the root (or `data/`) on startup.
- [x] The `Game` table exists with the specified columns.
- [x] Uploading a CSV populates the SQLite database, not just memory.
- [x] Restarting the backend does not lose the data in the DB.

## Dev Agent Record
### Agent Model Used
Gemini 2.0 Flash

### Debug Log References
- DB Initialization and sync logic tested in `tests/test_persistence.py`.
- Verified `sqlmodel` installation and `PYTHONPATH` issues during testing.

### Completion Notes List
- Implemented `lifespan` in `api.py` for clean startup/shutdown.
- Added `GameStatus` and `AttentionLevel` Enums for type safety.
- Successfully imported `sample_library.csv` into SQLite on first run.

### File List
- `requirements.txt` (Modified)
- `src/models.py` (New)
- `src/database.py` (New)
- `src/api.py` (Modified)
- `tests/test_persistence.py` (New)

### Change Log
- 2025-12-21: Initial implementation of SQLite persistence layer.
