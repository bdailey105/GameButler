# Story 7.5: Basic Auto-Tagging (Heuristic)

**Epic:** Epic 7: Backlog Management & Attention Tracking
**Priority:** Low
**Status:** Ready for Review

## Description
To reduce manual effort, the system should guess the attention level based on Steam tags when importing games or when triggered by the user. This helps quickly organize a library of hundreds of games into "Casual" and "Focused" buckets.

## Technical Tasks
- [x] **Define Heuristics**: Create a mapping dictionary in the backend.
- [x] **Logic Implementation**:
    -   Function `apply_heuristics(game)`:
        -   If `attention_level` is not `unset`, skip.
        -   Check tags (comma/semicolon separated).
        -   If Focused tag found -> `focused`.
        -   Else if Casual tag found -> `casual`.
- [x] **Trigger Integration**:
    -   Run `apply_heuristics` during CSV upload in `api.py`.
    -   Add `POST /games/auto-tag` endpoint to process all `unset` games.
- [x] **UI Integration**:
    -   Add an "Auto-Tag Uncategorized" button in the Library view.

## Acceptance Criteria
- [x] New uploads automatically categorize obvious games.
- [x] Clicking "Auto-Tag" in the UI populates attention levels for existing `unset` games.
- [x] Manual overrides are never overwritten by the heuristic.

## Dev Agent Record
### Agent Model Used
Gemini 2.0 Flash

### Debug Log References
- Created `src/logic.py` for categorization rules.
- Added `POST /games/auto-tag` to `src/api.py`.
- Verified conflict resolution (Focused > Casual) in `tests/test_logic.py`.

### Completion Notes List
- Implemented heuristic mapping for common Steam tags.
- Added a "🪄 Auto-Tag" button to the Library UI.
- Integrated heuristics into the initial data import and subsequent uploads.

### File List
- `src/logic.py` (New)
- `src/api.py` (Modified)
- `frontend/src/api.js` (Modified)
- `frontend/src/App.jsx` (Modified)
- `frontend/src/App.css` (Modified)
- `tests/test_logic.py` (New)

### Change Log
- 2025-12-21: Implemented heuristic auto-tagging for attention levels.