# Story 7.3: Frontend Library & Kanban View

**Epic:** Epic 7: Backlog Management & Attention Tracking
**Priority:** Medium
**Status:** Ready for Review

## Description
The user needs a visual interface to manage their game backlog. We will implement a "Dashboard" to track active games and a "Library" view to browse the full collection. We will use a simple Tab-based navigation to switch between the Recommendation Engine, Dashboard, and Library.

## Technical Tasks
- [x] **Navigation & Layout**:
    -   Update `App.jsx` to include a navigation bar/tabs: "Concierge" (Home), "Dashboard", "Library", "Upload".
    -   Implement state-based view switching (`currentView` state).
- [x] **API Integration**:
    -   Create `frontend/src/api.js` (or similar utility) to centralize Axios calls (`fetchGames`, `updateGame`).
- [x] **Dashboard View Component**:
    -   Fetch games with `status=playing` and `status=up_next`.
    -   Display two columns/sections: "Currently Playing" and "Up Next".
    -   Game Cards in these sections should have a "Finish" (Move to Completed) or "Drop" (Move to Abandoned/Library) button.
- [x] **Library View Component**:
    -   Fetch all games (default `status=library`? or all and client-side filter? Let's use server-side filter for `status=library` by default).
    -   Implement a Search Bar (uses `search` query param).
    -   Display games in a grid or list.
    -   Action: "Play Next" button on cards (moves status to `up_next`).
- [x] **Game Card Component**:
    -   Refactor existing display into a reusable `GameCard` component.
    -   Props: `game`, `onMove`, `showActions`.

## Acceptance Criteria
- [x] User can switch between "Concierge" (Recommendation), "Dashboard", and "Library".
- [x] **Dashboard**: Shows "Playing" and "Up Next" lists correctly populated from DB.
- [x] **Library**: Shows "Unsorted/Library" games, searchable by name.
- [x] **Actions**:
    -   Clicking "Add to Up Next" in Library moves the game to the Dashboard's "Up Next" column.
    -   Clicking "Start Playing" in "Up Next" moves it to "Playing".
    -   Clicking "Finish" in "Playing" moves it to "Completed" (and removes it from view).
- [x] UI updates immediately (optimistic) or re-fetches after action.

## Dev Agent Record
### Agent Model Used
Gemini 2.0 Flash

### Debug Log References
- Verified Axios integration with new backend endpoints.
- Implemented state-based routing within `App.jsx`.
- Styled responsive columns for Dashboard.

### Completion Notes List
- Refactored `App.jsx` into functional sub-components for better maintainability.
- Added optimistic UI updates for moving games between lists.
- Implemented real-time search in the Library view.

### File List
- `frontend/src/api.js` (New)
- `frontend/src/App.jsx` (Modified)
- `frontend/src/App.css` (Modified)

### Change Log
- 2025-12-21: Implemented Frontend Backlog and Kanban views.