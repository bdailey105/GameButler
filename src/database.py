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

def add_game_platform_column(connection):
    tables = {
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "game" not in tables:
        return

    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
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

def add_game_average_playtime_column(connection):
    tables = {
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "game" not in tables:
        return

    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
    if "average_playtime" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN average_playtime INTEGER")

def add_game_attention_source_column(connection):
    tables = {
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "game" not in tables:
        return

    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
    if "attention_source" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN attention_source TEXT")
    if "attention_level" not in columns:
        return
    # Conservative backfill: existing non-unset categorizations might be hand-set,
    # so treat them as manual rather than risk overwriting user intent later.
    connection.exec_driver_sql(
        "UPDATE game SET attention_source = 'manual' WHERE attention_level != 'unset' AND attention_source IS NULL"
    )

def add_game_enrich_attempts_column(connection):
    tables = {
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "game" not in tables:
        return

    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
    if "enrich_attempts" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN enrich_attempts INTEGER NOT NULL DEFAULT 0")

def add_game_personal_context_columns(connection):
    tables = {
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "game" not in tables:
        return

    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
    if "personal_rating" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN personal_rating INTEGER")
    if "started_on" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN started_on DATE")
    if "completed_on" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN completed_on DATE")
    if "current_note" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN current_note TEXT")

def add_game_session_tags_column(connection):
    tables = {
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "game" not in tables:
        return

    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
    if "session_tags" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN session_tags TEXT")

def add_game_return_when_column(connection):
    tables = {
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "game" not in tables:
        return

    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
    if "return_when" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN return_when TEXT")

def add_game_source_identity_columns(connection):
    tables = {
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if "game" not in tables:
        return

    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
    if "source" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN source TEXT")
    if "external_id" not in columns:
        connection.exec_driver_sql("ALTER TABLE game ADD COLUMN external_id TEXT")

    # Partial index: NULL source/external_id rows (existing Steam/manual games) are
    # exempt, so backfilled rows can never collide on the uniqueness rule.
    connection.exec_driver_sql(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_game_source_external
        ON game(source, external_id)
        WHERE source IS NOT NULL AND external_id IS NOT NULL
        """
    )

MIGRATIONS = (
    ("20260706_001_game_rich_metadata", add_game_rich_metadata_columns),
    ("20260706_002_game_queue_position", add_game_queue_position_column),
    # New columns need NEW migration ids — already-applied migrations never re-run
    ("20260708_003_game_platform", add_game_platform_column),
    ("20260708_004_game_average_playtime", add_game_average_playtime_column),
    ("20260708_005_game_attention_source", add_game_attention_source_column),
    ("20260709_006_game_enrich_attempts", add_game_enrich_attempts_column),
    ("20260709_007_game_personal_context", add_game_personal_context_columns),
    ("20260709_008_game_session_tags", add_game_session_tags_column),
    ("20260709_009_game_return_when", add_game_return_when_column),
    ("20260710_010_game_source_identity", add_game_source_identity_columns),
)

def get_session() -> Generator[Session, None, None]:
    """Dependency for obtaining a database session."""
    with Session(engine) as session:
        yield session
