# Story 8.1: Steam Metadata Service

**Epic:** Epic 8: Metadata Enrichment
**Priority:** High
**Status:** Ready for Dev

## Description
We need a robust backend service to fetch game details from the public Steam Store API. This service must handle network requests, parse the specific JSON format of the Steam API, and robustly handle rate limiting (HTTP 429) to avoid getting the user's IP banned.

## Technical Tasks
1.  **Create Service Module**: `src/steam_client.py`.
2.  **Implement Fetch Function**:
    -   `fetch_game_details(app_id: int) -> dict`
    -   URL: `http://store.steampowered.com/api/appdetails?appids={app_id}`
    -   Response Check: `success: true`. If false, game might be delisted or invalid.
3.  **Data Extraction**:
    -   Extract `genres` (list of descriptions).
    -   Extract `categories` (list of descriptions).
    -   Extract `header_image` (URL).
    -   Extract `short_description`.
4.  **Error Handling**:
    -   Handle connection errors.
    -   **Critical**: Handle Rate Limits. If 429 received, sleep and retry? Or raise exception for caller to handle. (Caller handling is better for batch processes).

## Acceptance Criteria
-   Calling `fetch_game_details(1086940)` (Baldur's Gate 3) returns a dict with "RPG", "Strategy", etc.
-   Service returns `None` or raises specific error if AppID is invalid.
-   Dependencies (`httpx` or `requests`) are used efficiently.

## Dev Agent Record
### Agent Model Used
Gemini 2.0 Flash
