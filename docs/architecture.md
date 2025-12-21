# GameButler Brownfield Architecture Document

## Introduction

This document captures the CURRENT STATE of the GameButler codebase. It serves as a reference for AI agents and developers working on the project. GameButler is a personal gaming concierge application that recommends games from a user's Steam library based on various filters.

### Document Scope

Comprehensive documentation of the entire system (Backend API, Frontend Web UI, and Recommendation Engine).

### Change Log

| Date       | Version | Description                 | Author |
| :--------- | :------ | :-------------------------- | :----- |
| 2025-12-21 | 1.0     | Initial brownfield analysis | PM Agent |

## Quick Reference - Key Files and Entry Points

### Critical Files for Understanding the System

-   **Backend Entry**: `src/api.py` (FastAPI application entry point)
-   **Frontend Entry**: `frontend/src/main.jsx` (React application entry point)
-   **Core Logic**: `src/recommender.py` (Recommendation algorithm and filtering logic)
-   **Data Loading**: `src/data_loader.py` (CSV parsing and normalization)
-   **Configuration**: `frontend/.env.development` (Frontend config), `Dockerfile.backend`, `Dockerfile.frontend`
-   **Data**: `data/sample_library.csv` (Default dataset)

## High Level Architecture

### Technical Summary

GameButler is a containerized full-stack application. The backend is a Python-based REST API using FastAPI that processes CSV data using Pandas. The frontend is a Single Page Application (SPA) built with React and Vite.

### Actual Tech Stack

| Category | Technology | Version | Notes |
| :--- | :--- | :--- | :--- |
| **Backend** | Python | 3.9+ | Slim image used in Docker |
| **Framework** | FastAPI | 0.1.0 (App) | running on Uvicorn |
| **Data Processing** | Pandas | (latest) | Used for in-memory CSV manipulation |
| **Frontend** | React | 19.2.0 | Built with Vite 7.2.4 |
| **HTTP Client** | Axios | 1.13.2 | For API communication |
| **Containerization** | Docker | - | Dockerfiles for both FE and BE |

### Repository Structure Reality Check

-   **Type**: Hybrid / Monorepo-ish (Backend and Frontend in same repo)
-   **Package Manager**: `pip` (Backend), `npm` (Frontend)

## Source Tree and Module Organization

### Project Structure (Actual)

```text
GameButler/
├── src/                     # Backend Source
│   ├── api.py               # FastAPI app and endpoints
│   ├── recommender.py       # Recommendation logic class
│   ├── data_loader.py       # Data ingestion utilities
│   ├── cli.py               # Legacy/Alternative CLI entry point
│   └── __init__.py
├── frontend/                # Frontend Source
│   ├── src/
│   │   ├── App.jsx          # Main UI Component
│   │   ├── main.jsx         # Entry point
│   │   ├── App.css          # Styling
│   │   └── assets/
│   ├── package.json
│   ├── vite.config.js
│   └── .env.development
├── data/                    # Data Storage
│   ├── sample_library.csv   # Default fallback data
│   └── [user uploads]       # Temporary storage location
├── tests/                   # Backend Tests
│   ├── test_recommender.py
│   └── test_data_loader.py
├── Dockerfile.backend       # Backend container config
├── Dockerfile.frontend      # Frontend container config
├── docker-compose.yml       # Orchestration (implied/referenced)
├── requirements.txt         # Backend dependencies
└── BACKLOG.md               # Project tracking
```

### Key Modules and Their Purpose

-   **API Layer**: `src/api.py` - Defines REST endpoints (`/upload`, `/recommend`) and manages the global `recommender` instance.
-   **Recommendation Engine**: `src/recommender.py` - Core business logic. Filters Pandas DataFrame based on genre, tags, playtime, and "unplayed" status.
-   **Frontend UI**: `frontend/src/App.jsx` - Handles user interaction, file selection, parameter setting, and displaying results.

## Data Models and APIs

### Data Models

Data is primarily handled as Pandas DataFrames.

-   **Game Record** (derived from CSV):
    -   `AppID` (int): Steam Application ID
    -   `Name` (str): Game Title
    -   `Playtime_Forever` (int): Total minutes played
    -   `Genre` (str): Semicolon-separated list of genres
    -   `Tags` (str): Semicolon-separated list of tags
    -   `Average_Playtime` (int, optional): Time to beat/length metric

### API Specifications

**Base URL**: `http://localhost:8000` (Local Dev)

#### 1. Upload Library
-   **Endpoint**: `POST /upload`
-   **Body**: `multipart/form-data` (`file`: CSV)
-   **Description**: Uploads a Steam library export. Temporarily saves and re-initializes the recommender.

#### 2. Get Recommendation
-   **Endpoint**: `GET /recommend`
-   **Query Parameters**:
    -   `genre` (str, optional): Substring match
    -   `tag` (str, optional): Substring match
    -   `unplayed_only` (bool, default `False`)
    -   `length` (str, optional): `short` (<5h), `medium` (5-20h), `long` (>20h)
-   **Response**: JSON object representing a single game (AppID, Name, Playtime, Genre, Tags).

## Technical Debt and Known Issues

### Critical Technical Debt

1.  **State Management**: The backend relies on a global `recommender` variable (`src/api.py`). This is not thread-safe or scalable for multiple users. It implies a single-user session model.
2.  **Data Persistence**: Uploaded files are saved as `temp_{filename}` and then removed. The system resets to `sample_library.csv` on restart or relies on re-uploading.
3.  **Hardcoded Paths**: References to `../data` in `api.py` rely on specific relative directory structure.

### Workarounds

-   **CORS**: `allow_origins=["*"]` is enabled globally in `src/api.py`, which is insecure for production.

## Integration Points

-   **Internal**: Frontend talks to Backend via standard HTTP (Axios).
-   **External**: None currently (data is ingested via CSV file). Future scope implies "Cloud Deployment" and potentially "Real Data Ingestion" via Steam API (though currently CSV based).

## Development and Deployment

### Local Development Setup

**Backend**:
1.  `python -m venv .venv`
2.  `source .venv/bin/activate`
3.  `pip install -r requirements.txt`
4.  `uvicorn src.api:app --reload`

**Frontend**:
1.  `cd frontend`
2.  `npm install`
3.  `npm run dev`

### Build and Deployment

-   **Docker**:
    -   `docker build -t gamebutler-backend -f Dockerfile.backend .`
    -   `docker build -t gamebutler-frontend -f Dockerfile.frontend .`

## Testing Reality

-   **Framework**: `pytest`
-   **Coverage**: Unit tests exist for `recommender` and `data_loader` in `tests/`.
-   **Running Tests**: `pytest` from the root directory.

