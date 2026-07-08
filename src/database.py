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
    run_migrations()

def run_migrations():
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        applied = {
            row[0]
            for row in connection.exec_driver_sql("SELECT id FROM schema_migrations")
        }

        for migration_id, migration in MIGRATIONS:
            if migration_id in applied:
                continue
            migration(connection)
            connection.exec_driver_sql(
                "INSERT INTO schema_migrations (id) VALUES (?)",
                (migration_id,),
            )

def ensure_game_columns():
    """Backward-compatible wrapper for older tests/callers."""
    run_migrations()

def add_game_rich_metadata_columns(connection):
    tables = {
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "game" not in tables:
        return

    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
    if "header_image" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN header_image TEXT")
    if "short_description" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN short_description TEXT")
    if "platform" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN platform TEXT NOT NULL DEFAULT 'steam'")

def add_game_queue_position_column(connection):
    tables = {
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "game" not in tables:
        return

    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
    if "queue_position" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN queue_position INTEGER")
    if "status" not in columns:
        return
    queued_ids = [
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT id FROM game WHERE status = 'up_next' AND queue_position IS NULL ORDER BY id"
        )
    ]
    for position, app_id in enumerate(queued_ids, start=1):
        connection.exec_driver_sql(
            "UPDATE game SET queue_position = ? WHERE id = ?",
            (position, app_id),
        )

MIGRATIONS = (
    ("20260706_001_game_rich_metadata", add_game_rich_metadata_columns),
    ("20260706_002_game_queue_position", add_game_queue_position_column),
)

def get_session() -> Generator[Session, None, None]:
    """Dependency for obtaining a database session."""
    with Session(engine) as session:
        yield session
