# Story 7.2: Backend API for Library Management

**Epic:** Epic 7: Backlog Management & Attention Tracking
**Priority:** High
**Status:** Ready for Review

## Description
With the persistence layer established in 7.1, we need to expose the library data via REST endpoints. This will enable the frontend to display the user's backlog and allow them to manage game states and attention levels.

## Technical Tasks
- [x] **Dependency Injection**: Use `get_session` from `src.database` in all new endpoints.
- [x] **GET /games**:
    -   Implement a list endpoint in `src/api.py`.
    -   Query Parameters: 
        -   `status`: Filter by `library`, `up_next`, `playing`, `completed`, `abandoned`.
        -   `attention_level`: Filter by `casual`, `focused`, `unset`.
        -   `search`: Case-insensitive substring match on game names.
    -   Response: List of `Game` objects (using the SQLModel/Pydantic schema).
- [x] **PUT /games/{app_id}**:
    -   Implement an update endpoint.
    -   Request Body: Use `GameUpdate` model from `src/models.py`.
    -   Logic:
        -   Retrieve game by `app_id`. Raise 404 if not found.
        -   Apply updates from the request body.
        -   Commit to DB.
        -   **CRITICAL**: Sync the global `recommender` instance if any relevant data changes (or rely on the fact that `recommender` reads from DB).
    -   Response: The updated `Game` object.
- [x] **Refactor /recommend**:
    -   Ensure the recommendation engine filters out games with status `completed` or `abandoned` by default.
    -   Add `attention_level` (str) as an optional query parameter to the `/recommend` endpoint.

## Acceptance Criteria
- [x] `GET /games` works and respects `status` and `attention_level` filters.
- [x] `PUT /games/{app_id}` successfully updates both `status` and `attention_level`.
- [x] Updating a game's status to `playing` is reflected in subsequent `GET /games?status=playing` calls.
- [x] `GET /recommend?attention_level=casual` returns a game tagged as `casual`.
- [x] API documentation (Swagger/Redoc) is updated automatically and correctly reflects the new models.

## Dev Agent Record
### Agent Model Used
Gemini 2.0 Flash

### Debug Log References
- `tests/test_api.py` verifies all new endpoints.
- `StaticPool` used for in-memory SQLite testing to avoid threading issues.

### Completion Notes List
- Implemented `GET /games` with search and filters.
- Implemented `PUT /games/{id}` with partial updates via Pydantic.
- Updated `src/recommender.py` to filter by attention level.
- Updated `src/api.py` to sync recommender after updates.
- Added `httpx` dependency for proper API testing.

### File List
- `src/api.py` (Modified)
- `src/recommender.py` (Modified)
- `tests/test_api.py` (New)
- `requirements.txt` (Modified)

### Change Log
- 2025-12-21: Implemented backend API for backlog management.