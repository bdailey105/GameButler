# Epic 8: Metadata Enrichment

**Goal:** Automatically populate game Genres, Tags, and Cover Art by fetching data from the Steam Store.

## Status
**Status:** Planned
**Priority:** High

## Context
The user's imported library (whether via CSV or API) often lacks rich metadata like "Roguelike", "Story Rich", or "Co-op". This metadata is critical for the "Attention Level" heuristics and for making informed decisions on what to play.

## User Stories

### Story 8.1: Steam Metadata Service
**As a** Developer,
**I want** a backend service that can fetch game details from the Steam Store,
**So that** I can fill in missing Genres and Tags.

**Acceptance Criteria:**
-   Function `fetch_steam_metadata(app_id)` implemented.
-   Fetches from `store.steampowered.com/api/appdetails`.
-   Parses response to extract: `genres` (list), `categories` (tags), `header_image` (url), `short_description`.
-   Handles 429 (Rate Limit) errors gracefully (backoff/retry).

### Story 8.2: Batch Enrichment Endpoint
**As a** User,
**I want** to update my entire library with new metadata,
**So that** I don't have to click "Refresh" on every single game.

**Acceptance Criteria:**
-   `POST /games/enrich` endpoint.
-   Iterates through games with missing data (e.g., Genre="Unknown").
-   Processes them in batches (e.g., 10 at a time) with a delay to respect rate limits.
-   Updates the database with new info.
-   Returns progress or a job ID (for MVP, maybe just streams progress or returns "Started").

### Story 8.3: Enrichment UI & Progress
**As a** User,
**I want** to see the enrichment progress and results,
**So that** I know when my library is ready to be categorized.

**Acceptance Criteria:**
-   "Enrich Library" button in the Library view.
-   (Nice to have) Progress indicator (e.g., "Enriching... 5/100").
-   Visual update: Games stop showing "Unknown" tags.
-   Cover art is displayed on the Game Card if available.
