# GameButler Backlog

## Epic 1: MVP CLI Game Recommender
**Goal:** A local command-line tool that ingests a Steam CSV and suggests a game to play.
- [x] **Story 1.1: Project Skeleton & Environment**
- [x] **Story 1.2: Data Ingestion**
- [x] **Story 1.3: Recommendation Engine (Basic)**
- [x] **Story 1.4: CLI Interface**

## Epic 2: Recommendation Engine Improvements
**Goal:** Smarter recommendations based on more data points.
- [x] **Story 2.1: Genre & Tag Filtering**
- [x] **Story 2.2: Time-to-Beat Integration**

## Epic 3: Web API (Backend)
**Goal:** Expose the recommendation logic via a REST API.
- [x] **Story 3.1: API Framework Setup**
- [x] **Story 3.2: Upload Endpoint**
- [x] **Story 3.3: Recommendation Endpoint**

## Epic 4: Web UI (Frontend)
**Goal:** A modern web interface for the butler.
- [x] **Story 4.1: React App Setup**
- [x] **Story 4.2: UI Implementation**

## Epic 5: Deployment
**Goal:** Deploy to a live environment.
- [x] **Story 5.1: Dockerization**
- [ ] **Story 5.2: Cloud Deployment**

## Epic 6: Real Data Ingestion
**Goal:** Support the user's actual Steam library export format.
- [x] **Story 6.1: Data Mapping & Normalization**
  - Map `game` -> `Name`, `id` -> `AppID`, `hours` -> `Playtime_Forever`.
  - Handle missing hours (treat as 0).
  - Handle missing Genre/Tags (fetch or mock? For now, mock/default).
- [x] **Story 6.2: Loader Update**
  - Update `load_steam_library` to auto-detect columns and normalize.

## Epic 7: Backlog Management & Attention Tracking
**Goal:** Track status (Playing, Next) and categorize by Attention Level (Casual vs Focused).
- [x] **Story 7.1: Persistence Layer Setup (SQLite)**
- [x] **Story 7.2: Backend API for Library Management**
- [x] **Story 7.3: Frontend Library & Kanban View**
- [x] **Story 7.4: Attention Level Categorization UI**
- [ ] **Story 7.5: Basic Auto-Tagging (Heuristic)**
