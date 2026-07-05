import os
from sqlmodel import create_engine, SQLModel, Session
from typing import Generator

# Database file location
# Using a path relative to the project root for consistency
DB_FILE = "data/gamebutler.db"
sqlite_url = f"sqlite:///{DB_FILE}"

# Ensure data directory exists for Docker volumes and fresh checkouts
os.makedirs("data", exist_ok=True)

# echo=True is helpful for debugging development SQL queries
engine = create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})

def init_db():
    """Create the database and tables."""
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """Dependency for obtaining a database session."""
    with Session(engine) as session:
        yield session
