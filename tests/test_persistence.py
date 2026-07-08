import pytest
import os
from sqlmodel import Session, select, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from src.models import Game, GameStatus, AttentionLevel
from src.recommender import GameRecommender
from src.database import ensure_game_columns, run_migrations
import pandas as pd
from unittest.mock import patch

# Use an in-memory database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

def test_game_creation(session: Session):
    game = Game(id=1, name="Test Game", playtime_forever=100)
    session.add(game)
    session.commit()
    
    statement = select(Game).where(Game.name == "Test Game")
    results = session.exec(statement).all()
    assert len(results) == 1
    assert results[0].name == "Test Game"
    assert results[0].status == GameStatus.LIBRARY

def test_game_rich_metadata_persists(session: Session):
    game = Game(
        id=1,
        name="Test Game",
        playtime_forever=100,
        header_image="https://example.com/header.jpg",
        short_description="A short Steam description.",
    )
    session.add(game)
    session.commit()

    result = session.get(Game, 1)
    assert result.header_image == "https://example.com/header.jpg"
    assert result.short_description == "A short Steam description."
    assert result.queue_position is None

def test_existing_game_table_gets_rich_metadata_columns():
    old_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with old_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE game (id INTEGER PRIMARY KEY, name TEXT, playtime_forever INTEGER)"
        )
        connection.exec_driver_sql(
            "INSERT INTO game (id, name, playtime_forever) VALUES (1, 'Old Game', 0)"
        )

    with patch("src.database.engine", old_engine):
        ensure_game_columns()

    with old_engine.connect() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
    assert "header_image" in columns
    assert "short_description" in columns
    assert "queue_position" in columns

def test_queue_position_migration_backfills_existing_queue():
    old_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with old_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE game (id INTEGER PRIMARY KEY, name TEXT, playtime_forever INTEGER, status TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO game (id, name, playtime_forever, status) VALUES (2, 'Second', 0, 'up_next')"
        )
        connection.exec_driver_sql(
            "INSERT INTO game (id, name, playtime_forever, status) VALUES (1, 'First', 0, 'up_next')"
        )

    with patch("src.database.engine", old_engine):
        run_migrations()

    with old_engine.connect() as connection:
        queue = connection.exec_driver_sql(
            "SELECT id, queue_position FROM game ORDER BY queue_position"
        ).all()

    assert queue == [(1, 1), (2, 2)]

def test_migrations_are_recorded_and_idempotent():
    old_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with old_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE game (id INTEGER PRIMARY KEY, name TEXT, playtime_forever INTEGER)"
        )

    with patch("src.database.engine", old_engine):
        run_migrations()
        run_migrations()

    with old_engine.connect() as connection:
        migrations = connection.exec_driver_sql("SELECT id FROM schema_migrations").all()
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}

    assert migrations == [
        ("20260706_001_game_rich_metadata",),
        ("20260706_002_game_queue_position",),
        ("20260708_003_game_platform",),
    ]
    assert "header_image" in columns
    assert "short_description" in columns
    assert "platform" in columns

def test_platform_migration_runs_on_db_with_earlier_migrations_applied():
    """Regression: adding a column to an already-applied migration never runs.
    Simulates a production DB where 001/002 are recorded but platform is missing."""
    old_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with old_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE game (id INTEGER PRIMARY KEY, name TEXT, playtime_forever INTEGER, "
            "header_image TEXT, short_description TEXT, queue_position INTEGER)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE schema_migrations (id TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "INSERT INTO schema_migrations (id) VALUES ('20260706_001_game_rich_metadata'), ('20260706_002_game_queue_position')"
        )
        connection.exec_driver_sql(
            "INSERT INTO game (id, name, playtime_forever) VALUES (1, 'Existing Game', 42)"
        )

    with patch("src.database.engine", old_engine):
        run_migrations()

    with old_engine.connect() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
        platform = connection.exec_driver_sql("SELECT platform FROM game WHERE id = 1").scalar()

    assert "platform" in columns
    assert platform == "steam"
    assert "queue_position" in columns

def test_recommender_sync_logic(session: Session):
    # Add some games
    session.add(Game(id=1, name="Game A", playtime_forever=0, genre="Action", tags="Indie"))
    session.add(Game(id=2, name="Game B", playtime_forever=100, genre="RPG", tags="Story Rich"))
    session.commit()
    
    # Simulate the sync logic from api.py
    statement = select(Game)
    results = session.exec(statement).all()
    data = [game.model_dump() for game in results]
    df = pd.DataFrame(data)
    df = df.rename(columns={
        'id': 'AppID',
        'name': 'Name',
        'playtime_forever': 'Playtime_Forever',
        'genre': 'Genre',
        'tags': 'Tags'
    })
    
    recommender = GameRecommender(df)
    assert len(recommender.df) == 2
    
    # Test recommendation
    rec = recommender.recommend(genre="Action")
    assert rec['Name'] == "Game A"
