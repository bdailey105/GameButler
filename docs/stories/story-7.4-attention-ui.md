# Story 7.4: Attention Level Categorization UI

**Epic:** Epic 7: Backlog Management & Attention Tracking
**Priority:** Medium
**Status:** Ready for Review

## Description
Users need to be able to tag games as "Casual" or "Focused" and then filter recommendations based on this. This story adds the UI controls to manage these tags and utilize them in the recommendation engine.

## Technical Tasks
- [x] **Game Card Update**:
    -   Add visual indicators for "Casual" and "Focused".
    -   Add a toggle button or segmented control to switch between: `unset`, `casual`, `focused`.
    -   Trigger `updateGame` API call on change.
- [x] **ConciergeView (Recommendation) Filter Update**:
    -   Add an "Attention" dropdown or radio group to the filter panel.
    -   Options: "Any", "Casual", "Focused".
    -   Pass the selected `attention_level` as a query parameter to `GET /recommend`.
- [x] **Library View Filter**:
    -   Add a small filter to the Library view to filter by Attention Level (e.g., "Show Uncategorized").

## Acceptance Criteria
- [x] User can toggle a game between "Casual", "Focused", and "Unset" from any view.
- [x] The game card updates visually to reflect the current attention level.
- [x] The recommendation filter successfully requests specific attention levels.
- [x] The recommendation engine respects this filter.

## Dev Agent Record
### Agent Model Used
Gemini 2.0 Flash

### Debug Log References
- Added `onAttentionChange` callback to `GameCard`.
- Updated `LibraryView` to support multi-parameter filtering (search + attention).
- Added CSS border-left indicators for active attention categories.

### Completion Notes List
- Implemented tri-state toggle for attention levels on all game cards.
- Added attention level display to the Butler's recommendation result.
- Added "Uncategorized" filter option to help user clean up their library.

### File List
- `frontend/src/App.jsx` (Modified)
- `frontend/src/App.css` (Modified)

### Change Log
- 2025-12-21: Implemented Attention Level UI and filtering logic.