# GameButler Product Requirements Document (PRD)

## 1. Introduction

### 1.1 Purpose
GameButler is a personal gaming concierge designed to help users manage their backlog, decide what to play next, and track their gaming habits. It addresses "choice paralysis" and helps categorize games based on the required user attention (Casual vs. Focused).

### 1.2 Scope
The product encompasses a recommendation engine, a RESTful API, and a web-based user interface. It supports ingesting user Steam library data, filtering based on preferences (time, genre, tags, attention level), and managing the user's "To Play" and "Playing" lists.

## 2. Product Overview

### 2.1 Current State Summary
As of Dec 2025, GameButler is a functional MVP with:
-   **Full-Stack Architecture**: Python FastAPI backend + React Vite frontend.
-   **Core Recommendation Engine**: Can ingest Steam CSVs and recommend games based on Genre, Tags, Playtime, and Game Length.
-   **Containerization**: Dockerized for local development/deployment.
-   **Data**: Currently relies on ephemeral CSV uploads or a static sample file.

### 2.2 User Problem
Users with extensive Steam libraries struggle to:
1.  Choose a game from hundreds of options.
2.  Differentiate between "Casual/Podcast" games (low attention) and "Focused" games (high immersion).
3.  Keep track of what they are currently playing versus what they intend to play next, separate from the massive "Unplayed" pile.

### 2.3 Solution
An interactive tool that:
-   **Ingests & Categorizes**: Import library and allow tagging games by "Attention Level" (Casual vs. Focused).
-   **Manages Backlog**: Moves games between "Backlog" (All), "Up Next" (Queue), "Playing" (Active), and "Completed" (History).
-   **Intelligent Recommendations**: Suggests games based on the user's current mental bandwidth (e.g., "I just want to zone out" -> Recommend Vampire Survivors).

## 3. Key Features

### 3.1 Data Ingestion (Existing)
-   **CSV Upload**: Users can upload their Steam library exported as a CSV file.
-   **Normalization**: The system normalizes data (handling missing playtimes, mapping columns).

### 3.2 Recommendation Engine (Enhanced)
-   **Existing Filters**: Genre, Tags, Playtime (Unplayed), Game Length.
-   **New Filter: Attention Level**:
    -   **Casual**: Low cognitive load, playable while multitasking (e.g., Vampire Survivors).
    -   **Focused**: High immersion, story-driven, requires full attention (e.g., Cyberpunk 2077).

### 3.3 Backlog Management (New)
-   **Kanban-style Tracking**:
    -   **Library**: The full imported list.
    -   **Up Next**: User-selected queue of high-priority games.
    -   **Playing**: Currently active games.
    -   **Completed**: Games finished.
-   **Manual & Auto Categorization**: Ability to manually tag games as Casual/Focused, or auto-tag based on known genres/tags (heuristic).

### 3.4 User Interfaces
-   **Web UI (React)**:
    -   **Dashboard**: Overview of "Playing" and "Up Next".
    -   **Library View**: Searchable, filterable list of all games.
    -   **Recommendation View**: The "Butler" suggesting a game.

### 3.5 API
-   **RESTful Endpoints**:
    -   `POST /upload`: Handle library ingestion.
    -   `GET /recommend`: Serve recommendation logic.
    -   **New**: `GET /library`, `PUT /game/{id}/status`, `PUT /game/{id}/attention`.

## 4. Technical Requirements

-   **Backend**: Python (FastAPI).
-   **Frontend**: React (Vite).
-   **Persistence**: Need to move from ephemeral CSV/Memory to a persistent database (SQLite/PostgreSQL) to store user-defined tags (Attention Level) and Status (Playing/Next).
-   **Deployment**: Dockerized containers.

## 5. Roadmap & Status

| Feature / Epic | Status | Notes |
| :--- | :--- | :--- |
| **MVP CLI Tool** | **Done** | Basic recommendation logic implemented. |
| **Engine Improvements** | **Done** | Added filters for Genre, Tags, Time-to-beat. |
| **Web API** | **Done** | FastAPI implementation complete. |
| **Web UI** | **Done** | React frontend operational. |
| **Real Data Support** | **Done** | CSV parsing and normalization active. |
| **Cloud Deployment** | **Pending** | Docker files exist; cloud infra setup pending (Epic 5.2). |
| **Backlog Management** | **Planned** | Track "Playing", "Up Next", and "Attention Level" (Casual vs Focused). |