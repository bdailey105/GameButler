import pytest
import os
from sqlmodel import Session, select, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from sqlalchemy.exc import IntegrityError
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
        ("20260708_004_game_average_playtime",),
        ("20260708_005_game_attention_source",),
        ("20260709_006_game_enrich_attempts",),
        ("20260709_007_game_personal_context",),
        ("20260709_008_game_session_tags",),
        ("20260709_009_game_return_when",),
        ("20260710_010_game_source_identity",),
    ]
    assert "header_image" in columns
    assert "short_description" in columns
    assert "platform" in columns
    assert "average_playtime" in columns
    assert "attention_source" in columns
    assert "enrich_attempts" in columns
    assert "personal_rating" in columns
    assert "started_on" in columns
    assert "completed_on" in columns
    assert "current_note" in columns
    assert "session_tags" in columns
    assert "return_when" in columns
    assert "source" in columns
    assert "external_id" in columns

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

def test_attention_source_migration_backfills_manual():
    """Existing categorizations made before attention_source existed are assumed
    hand-set, so the backfill marks them 'manual' rather than risk overwriting
    user intent by leaving them open to future auto-tag runs."""
    old_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with old_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE game (id INTEGER PRIMARY KEY, name TEXT, playtime_forever INTEGER, "
            "attention_level TEXT NOT NULL DEFAULT 'unset')"
        )
        connection.exec_driver_sql(
            "INSERT INTO game (id, name, playtime_forever, attention_level) VALUES (1, 'Old Game', 42, 'casual')"
        )

    with patch("src.database.engine", old_engine):
        run_migrations()

    with old_engine.connect() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
        attention_source = connection.exec_driver_sql(
            "SELECT attention_source FROM game WHERE id = 1"
        ).scalar()

    assert "attention_source" in columns
    assert attention_source == "manual"

def test_personal_context_migration_runs_on_db_with_earlier_migrations_applied():
    """Regression: adding a column to an already-applied migration never runs.
    Simulates a production DB where earlier migrations are recorded but the new
    personal-context columns are missing."""
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
            "INSERT INTO game (id, name, playtime_forever) VALUES (1, 'Existing Game', 42)"
        )

    with patch("src.database.engine", old_engine):
        run_migrations()

    with old_engine.connect() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
        row = connection.exec_driver_sql(
            "SELECT personal_rating, started_on, completed_on, current_note FROM game WHERE id = 1"
        ).first()

    assert "personal_rating" in columns
    assert "started_on" in columns
    assert "completed_on" in columns
    assert "current_note" in columns
    assert row == (None, None, None, None)

def test_game_personal_context_persists(session: Session):
    from datetime import date

    game = Game(
        id=1,
        name="Test Game",
        playtime_forever=100,
        personal_rating=4,
        started_on=date(2026, 1, 1),
        completed_on=date(2026, 2, 1),
        current_note="Stuck on the final boss.",
    )
    session.add(game)
    session.commit()

    result = session.get(Game, 1)
    assert result.personal_rating == 4
    assert result.started_on == date(2026, 1, 1)
    assert result.completed_on == date(2026, 2, 1)
    assert result.current_note == "Stuck on the final boss."

def test_session_tags_migration_runs_on_db_with_earlier_migrations_applied():
    """Regression: adding a column to an already-applied migration never runs.
    Simulates a production DB where earlier migrations are recorded but the new
    session_tags column is missing."""
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
            "INSERT INTO game (id, name, playtime_forever) VALUES (1, 'Existing Game', 42)"
        )

    with patch("src.database.engine", old_engine):
        run_migrations()

    with old_engine.connect() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
        session_tags = connection.exec_driver_sql(
            "SELECT session_tags FROM game WHERE id = 1"
        ).scalar()

    assert "session_tags" in columns
    assert session_tags is None

def test_game_session_tags_persists(session: Session):
    game = Game(
        id=1,
        name="Test Game",
        playtime_forever=100,
        session_tags="burst_friendly;controller_only",
    )
    session.add(game)
    session.commit()

    result = session.get(Game, 1)
    assert result.session_tags == "burst_friendly;controller_only"

def test_return_when_migration_runs_on_db_with_earlier_migrations_applied():
    """Regression: adding a column to an already-applied migration never runs.
    Simulates a production DB where earlier migrations are recorded but the new
    return_when column is missing."""
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
            "INSERT INTO game (id, name, playtime_forever) VALUES (1, 'Existing Game', 42)"
        )

    with patch("src.database.engine", old_engine):
        run_migrations()

    with old_engine.connect() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
        return_when = connection.exec_driver_sql(
            "SELECT return_when FROM game WHERE id = 1"
        ).scalar()

    assert "return_when" in columns
    assert return_when is None

def test_game_return_when_persists(session: Session):
    game = Game(
        id=1,
        name="Test Game",
        playtime_forever=100,
        status=GameStatus.PAUSED,
        return_when="the DLC drops",
    )
    session.add(game)
    session.commit()

    result = session.get(Game, 1)
    assert result.status == GameStatus.PAUSED
    assert result.return_when == "the DLC drops"

def test_source_identity_migration_runs_on_db_with_earlier_migrations_applied():
    """Regression: adding a column to an already-applied migration never runs.
    Simulates a production DB where earlier migrations are recorded but the new
    source/external_id columns are missing."""
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
            "INSERT INTO game (id, name, playtime_forever) VALUES (1, 'Existing Game', 42)"
        )

    with patch("src.database.engine", old_engine):
        run_migrations()

    with old_engine.connect() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(game)")}
        row = connection.exec_driver_sql(
            "SELECT source, external_id FROM game WHERE id = 1"
        ).first()

    assert "source" in columns
    assert "external_id" in columns
    assert row == (None, None)

def test_duplicate_source_external_id_raises_integrity_error():
    """Two games with the same (source, external_id) pair collide on the partial
    unique index, so a repeated import can never create a duplicate record."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    with patch("src.database.engine", test_engine):
        run_migrations()

    with Session(test_engine) as session:
        session.add(Game(id=1, name="Mario Kart 8", playtime_forever=0, source="nintendo_export", external_id="abc123"))
        session.commit()

        session.add(Game(id=2, name="Mario Kart 8 Deluxe", playtime_forever=0, source="nintendo_export", external_id="abc123"))
        with pytest.raises(IntegrityError):
            session.commit()

def test_games_with_null_source_coexist():
    """Existing Steam/manual games (source and external_id both NULL) are exempt
    from the partial unique index and can coexist without collision."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    with patch("src.database.engine", test_engine):
        run_migrations()

    with Session(test_engine) as session:
        session.add(Game(id=1, name="Manual Game 1", playtime_forever=0))
        session.add(Game(id=2, name="Manual Game 2", playtime_forever=0))
        session.commit()

        results = session.exec(select(Game)).all()
        assert len(results) == 2

def test_journal_entries_persist_and_round_trip(session: Session):
    from src.models import JournalEntry

    game = Game(id=1, name="Test Game", playtime_forever=100)
    session.add(game)
    session.commit()

    session.add(JournalEntry(game_id=1, text="Started the tutorial."))
    session.add(JournalEntry(game_id=1, text="Beat the first boss."))
    session.commit()

    entries = session.exec(
        select(JournalEntry).where(JournalEntry.game_id == 1)
    ).all()
    assert len(entries) == 2
    assert {entry.text for entry in entries} == {
        "Started the tutorial.",
        "Beat the first boss.",
    }
    assert all(entry.created_at is not None for entry in entries)

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

def test_recommendation_decision_persists_and_round_trips(session: Session):
    from src.models import RecommendationDecision

    game = Game(id=1, name="Test Game", playtime_forever=100, tags="Indie;Story Rich")
    session.add(game)
    session.commit()

    session.add(RecommendationDecision(
        game_id=1,
        decision="rejected",
        reason="too_long",
        mood="story_night",
        tags_snapshot=game.tags,
    ))
    session.commit()

    decisions = session.exec(
        select(RecommendationDecision).where(RecommendationDecision.game_id == 1)
    ).all()
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.decision == "rejected"
    assert decision.reason == "too_long"
    assert decision.mood == "story_night"
    assert decision.tags_snapshot == "Indie;Story Rich"
    assert decision.created_at is not None
