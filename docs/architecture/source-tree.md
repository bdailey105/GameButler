# Source Tree Organization

```text
GameButler/
├── src/                     # Backend Application Source
│   ├── api.py               # Main FastAPI application entry point
│   ├── recommender.py       # Core recommendation engine logic
│   ├── data_loader.py       # Data ingestion and normalization utilities
│   ├── cli.py               # CLI interface (legacy/alternative)
│   └── __init__.py
├── frontend/                # Frontend Application Source
│   ├── src/
│   │   ├── App.jsx          # Main React component
│   │   ├── main.jsx         # React DOM entry point
│   │   ├── App.css          # Application styles
│   │   └── assets/          # Static assets (images, icons)
│   ├── public/              # Public static files
│   ├── package.json         # Frontend dependencies and scripts
│   ├── vite.config.js       # Vite configuration
│   └── .env.development     # Development environment variables
├── data/                    # Data Storage
│   ├── sample_library.csv   # Default dataset provided with repo
│   └── [user uploads]       # Runtime location for uploaded CSVs
├── tests/                   # Backend Test Suite
│   ├── test_recommender.py
│   └── test_data_loader.py
├── docs/                    # Project Documentation
│   ├── architecture/        # Architectural details and standards
│   ├── prd.md               # Product Requirements Document
│   └── architecture.md      # Main Architecture overview
├── Dockerfile.backend       # Docker build instruction for Backend
├── Dockerfile.frontend      # Docker build instruction for Frontend
├── docker-compose.yml       # Container orchestration config
├── requirements.txt         # Python dependencies
└── BACKLOG.md               # Feature backlog and status
```
