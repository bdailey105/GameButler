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
- [x] **Story 5.2: ~~Cloud Deployment~~ (superseded by Epic 9: Home Network Deployment)**

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
- [x] **Story 7.5: Basic Auto-Tagging (Heuristic)**

## Epic 8: Metadata Enrichment
**Goal:** Automatically populate Genres, Tags, and Art from Steam.
- [x] **Story 8.1: Steam Metadata Service**
- [x] **Story 8.2: Batch Enrichment Endpoint**
- [x] **Story 8.3: Enrichment UI & Progress**

## Epic 9: Home Network Deployment
**Goal:** Run GameButler on an always-on home LAN host via Docker.
- [x] **Story 9.1: DB Persistence Fix** — SQLite file moved to `data/` so the Docker volume actually persists it across rebuilds.
- [x] **Story 9.2: LAN Deployment Guide** — Rewrote DEPLOY.md for home-network deployment (was VPS-focused).
- [x] **Story 9.3: Backlog Cleanup** — Marked shipped stories done, retired cloud deployment story.

## Epic 10: Loose Ends
**Goal:** Finish partially-implemented features.
- [x] **Story 10.1: Recommender Exclusion Filter** — Completed/Abandoned games are excluded from recommendations by default and covered by a regression test.
- [x] **Story 10.2: Enrichment Progress UI** — Frontend polls job status every 1.5s and shows progress.
- [x] **Story 10.3: Store Game Art & Descriptions** — header_image and short_description persisted and shown on game cards.

## Epic 11: Local Deployment Hardening
**Goal:** Make local and home-LAN deployment the supported production path.
- [x] **Story 11.1: One-command Local Bootstrap** — Added `make setup`, `make verify`, and local deployment commands.
- [x] **Story 11.2: Local Health Check Script** — Added `make health` to verify frontend, backend, DB file, and `/api/health` after `docker compose up`.
- [x] **Story 11.3: Backup/Restore Workflow** — Added `make backup`, `make restore BACKUP=...`, and deployment docs for SQLite recovery.

## Epic 12: Direct Steam Sync
**Goal:** Pull the library straight from the Steam Web API — no manual CSV export.
- [x] **Story 12.1: Steam Owned-Games Client & Sync Endpoint** — `fetch_owned_games` via IPlayerService/GetOwnedGames; `POST /sync/steam` upserts playtime/new games while preserving status, attention level, and enrichment data.
- [x] **Story 12.2: Sync Button in Library UI** — One-click "Sync Steam" in the library toolbar with success/error feedback.
- [x] **Story 12.3: Configuration & Docs** — `STEAM_API_KEY` / `STEAM_ID` env vars wired through Docker Compose and documented in DEPLOY.md.
