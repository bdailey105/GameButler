# Story 8.2: Batch Enrichment Endpoint

**Epic:** Epic 8: Metadata Enrichment
**Priority:** High
**Status:** Planned

## Description
We need an API endpoint to trigger the metadata update process. Since updating hundreds of games will take time (due to rate limits), this endpoint should probably run in the background or process a chunk of games.

## Technical Tasks
1.  **Enrichment Logic**:
    -   Function `enrich_games(session, limit=10)`:
        -   Find games where `genre == "Unknown"` (or new `metadata_updated` flag is false).
        -   Loop through them.
        -   Call `steam_client.fetch_game_details`.
        -   Update `Game` object.
        -   **Sleep**: `time.sleep(1.5)` between calls to be safe (Steam limit is roughly 200/5min, so ~1.5s is safe).
        -   Commit changes.
2.  **API Endpoint**:
    -   `POST /games/enrich`
    -   Optional param: `limit` (default 50).
    -   Returns: `{ "processed": 5, "updated": 5, "errors": 0 }`.
3.  **Database Update**:
    -   Update `Game` model to include `header_image` and `short_description` fields?
    -   Yes, we need to add these columns. (Migration needed? Or just `alembic`? For now, we can rely on SQLModel creating them if we drop/recreate, but preserving data is better. Since we are using SQLite and just `create_all`, adding columns to the model might require manual `ALTER TABLE` or using `alembic`. For this MVP, if we add fields, we might crash if we don't migrate.
    -   *Decision*: Let's stick to using the existing `genre` and `tags` columns for now to avoid DB migration complexity in this story. We can add `image_url` if we want, but let's see if we can do it safely. SQLite supports `ALTER TABLE ADD COLUMN`.

## Acceptance Criteria
-   `POST /games/enrich` updates the "Unknown" genres/tags in the database.
-   Rate limits are respected (process takes time but doesn't crash).
-   Recommender data is refreshed after enrichment.
