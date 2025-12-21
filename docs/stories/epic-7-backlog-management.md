# Epic 7: Backlog Management & Attention Tracking

**Goal:** Transform GameButler from a simple randomizer into a backlog management tool. Enable users to track what they are playing, plan what's next, and categorize games by required attention level (Casual vs. Focused).

## Status
**Status:** Planned
**Priority:** High

## Context
Users need more than just a random suggestion; they need to organize their gaming life. Specifically, they want to distinguish between "podcast games" (Casual) and immersive experiences (Focused) and track their progress.

## User Stories

### Story 7.1: Persistence Layer Setup
**As a** Developer,
**I want** to replace the in-memory/CSV storage with a persistent database (SQLite for MVP),
**So that** user changes (game status, attention tags) are saved between restarts.

**Acceptance Criteria:**
-   SQLite database initialized on startup.
-   Data model created for `Game` (AppID, Name, Genre, Tags, Playtime, Status, AttentionLevel).
-   Migration script (or logic) to import existing CSV data into the DB if empty.

### Story 7.2: Backend API for Library Management
**As a** Frontend Developer,
**I want** API endpoints to manage game state,
**So that** I can build the UI for the backlog.

**Acceptance Criteria:**
-   `GET /games`: List all games with support for filtering by Status and Attention.
-   `PUT /games/{app_id}`: Update `status` (Library, UpNext, Playing, Completed).
-   `PUT /games/{app_id}/attention`: Update `attention_level` (Casual, Focused).

### Story 7.3: Frontend Library & Kanban View
**As a** User,
**I want** to see my games organized by their current status,
**So that** I can easily manage my "Up Next" queue and see what I'm currently playing.

**Acceptance Criteria:**
-   New "Library" or "Dashboard" page.
-   Visual separation (Lists or Columns) for: Playing, Up Next, Backlog (Library), Completed.
-   Ability to move games between these states (Drag & drop or Dropdown).

### Story 7.4: Attention Level Categorization
**As a** User,
**I want** to tag games as "Casual" or "Focused",
**So that** the recommender can suggest games that match my current mental energy.

**Acceptance Criteria:**
-   UI indicator/toggle on Game Card for "Casual" vs "Focused".
-   Update Recommendation Filter to include "Attention Level" selector.
-   Backend logic updated to filter by this new field.

### Story 7.5: Basic Auto-Tagging (Heuristic)
**As a** User,
**I want** the system to guess if a game is Casual or Focused based on its tags,
**So that** I don't have to manually tag 500+ games.

**Acceptance Criteria:**
-   Logic implemented to map certain Steam tags to Attention Levels (e.g., "Story Rich" -> Focused, "Arcade" -> Casual).
-   Run this logic on import/first load.
-   User manual override persists and is not overwritten by auto-tagging.
