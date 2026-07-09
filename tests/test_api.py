from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
from src.api import app, get_session
from src.api import process_enrichment, enrichment_candidates_query, run_scheduled_enrichment
from src.api import run_steam_sync, steam_sync_interval_seconds
from src.models import Game, GameStatus, AttentionLevel, EnrichmentJob, PlayEvent, SyncRun, JournalEntry, RecommendationDecision
from src.recommender import GameRecommender
import pytest
import pandas as pd
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

# Test Database - In Memory with StaticPool to share connection across threads
TEST_DATABASE_URL = "sqlite://"
engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

def get_test_session():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_session] = get_test_session

@pytest.fixture(autouse=True)
def mock_lifespan():
    with patch("src.api.init_db") as mock_init, \
         patch("src.api.sync_recommender_with_db") as mock_sync:
        yield

@pytest.fixture(name="client")
def client_fixture():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    real_exists = os.path.exists
    with patch("src.api.engine", engine), \
         patch("src.api.os.path.exists", side_effect=lambda path: False if str(path).endswith("sample_library.csv") else real_exists(path)):
        with TestClient(app) as client:
            yield client
    SQLModel.metadata.drop_all(engine)

def test_list_games(client):
    # Setup data
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, status=GameStatus.LIBRARY))
        session.add(Game(id=2, name="Game B", playtime_forever=100, status=GameStatus.PLAYING))
        session.commit()

    response = client.get("/games")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Test Filter
    response = client.get("/games?status=playing")
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Game B"

def test_games_include_rich_metadata(client):
    with Session(engine) as session:
        session.add(Game(
            id=1,
            name="Game A",
            playtime_forever=0,
            header_image="https://example.com/header.jpg",
            short_description="A short Steam description.",
        ))
        session.commit()

    response = client.get("/games")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["header_image"] == "https://example.com/header.jpg"
    assert data[0]["short_description"] == "A short Steam description."

def test_update_game(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, status=GameStatus.LIBRARY))
        session.commit()

    response = client.put("/games/1", json={"status": "playing", "attention_level": "focused"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "playing"
    assert data["attention_level"] == "focused"

    # Verify persistence
    with Session(engine) as session:
        game = session.get(Game, 1)
        assert game.status == GameStatus.PLAYING
        assert game.attention_level == AttentionLevel.FOCUSED

def test_update_game_marks_attention_manual(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, status=GameStatus.LIBRARY))
        session.commit()

    response = client.put("/games/1", json={"attention_level": "focused"})
    assert response.status_code == 200
    assert response.json()["attention_source"] == "manual"

    with Session(engine) as session:
        game = session.get(Game, 1)
        assert game.attention_source == "manual"

    response = client.put("/games/1", json={"attention_level": "unset"})
    assert response.status_code == 200
    assert response.json()["attention_source"] is None

    with Session(engine) as session:
        game = session.get(Game, 1)
        assert game.attention_source is None

def test_update_game_sets_valid_session_tags(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, status=GameStatus.LIBRARY))
        session.commit()

    response = client.put("/games/1", json={"session_tags": "burst_friendly;podcast_friendly"})
    assert response.status_code == 200
    assert response.json()["session_tags"] == "burst_friendly;podcast_friendly"

    with Session(engine) as session:
        game = session.get(Game, 1)
        assert game.session_tags == "burst_friendly;podcast_friendly"

def test_update_game_rejects_invalid_session_tag(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, status=GameStatus.LIBRARY))
        session.commit()

    response = client.put("/games/1", json={"session_tags": "burst_friendly;not_a_real_tag"})
    assert response.status_code == 422

def test_queue_append_sort_and_reorder(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="First", playtime_forever=0, status=GameStatus.LIBRARY))
        session.add(Game(id=2, name="Second", playtime_forever=0, status=GameStatus.LIBRARY))
        session.add(Game(id=3, name="Third", playtime_forever=0, status=GameStatus.LIBRARY))
        session.commit()

    assert client.put("/games/1", json={"status": "up_next"}).json()["queue_position"] == 1
    assert client.put("/games/2", json={"status": "up_next"}).json()["queue_position"] == 2
    assert client.put("/games/3", json={"status": "up_next"}).json()["queue_position"] == 3

    response = client.put("/games/queue", json={"app_ids": [3, 1, 2]})

    assert response.status_code == 200
    assert [game["id"] for game in response.json()] == [3, 1, 2]
    assert [game["queue_position"] for game in response.json()] == [1, 2, 3]

    response = client.get("/games?status=up_next")
    assert [game["id"] for game in response.json()] == [3, 1, 2]

def test_queue_reorder_rejects_bad_input(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Queued", playtime_forever=0, status=GameStatus.UP_NEXT, queue_position=1))
        session.add(Game(id=2, name="Library", playtime_forever=0, status=GameStatus.LIBRARY))
        session.commit()

    assert client.put("/games/queue", json={"app_ids": [1, 1]}).status_code == 400
    assert client.put("/games/queue", json={"app_ids": [2]}).status_code == 400

    with Session(engine) as session:
        session.add(Game(id=3, name="Also Queued", playtime_forever=0, status=GameStatus.UP_NEXT, queue_position=2))
        session.commit()

    assert client.put("/games/queue", json={"app_ids": [1]}).status_code == 400

def test_queue_position_clears_when_removed(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Queued", playtime_forever=0, status=GameStatus.UP_NEXT, queue_position=1))
        session.commit()

    response = client.put("/games/1", json={"status": "library"})

    assert response.status_code == 200
    assert response.json()["queue_position"] is None

def test_recommend_returns_score_and_reasons(client):
    df = pd.DataFrame({
        "AppID": [1, 2],
        "Name": ["Library Game", "Queued Game"],
        "Playtime_Forever": [0, 20],
        "Average_Playtime": [120, 120],
        "Genre": ["Action", "Action"],
        "Tags": ["Indie", "Indie"],
        "status": [GameStatus.LIBRARY, GameStatus.UP_NEXT],
        "attention_level": [AttentionLevel.UNSET, AttentionLevel.CASUAL],
    })

    with patch("src.api.recommender", GameRecommender(df)):
        response = client.get("/recommend?genre=Action&attention_level=casual")

    assert response.status_code == 200
    data = response.json()
    assert data["Name"] == "Queued Game"
    assert data["score"] > 0
    assert "Already in your Up Next queue" in data["reasons"]
    assert "Matches your casual attention setting" in data["reasons"]

def test_recommend_accepts_mood_and_rejects_invalid_mood(client):
    df = pd.DataFrame({
        "AppID": [1, 2],
        "Name": ["Arcade Game", "Story Game"],
        "Playtime_Forever": [0, 0],
        "Average_Playtime": [120, 1200],
        "Genre": ["Action", "RPG"],
        "Tags": ["Arcade", "Story"],
        "status": [GameStatus.LIBRARY, GameStatus.LIBRARY],
        "attention_level": [AttentionLevel.CASUAL, AttentionLevel.FOCUSED],
    })

    with patch("src.api.recommender", GameRecommender(df)):
        response = client.get("/recommend?mood=zone_out")

    assert response.status_code == 200
    data = response.json()
    assert data["Name"] == "Arcade Game"
    assert "Mood: good for zoning out" in data["reasons"]

    response = client.get("/recommend?mood=chaos_mode")
    assert response.status_code == 422

def test_recommend_accepts_valid_session_params(client):
    df = pd.DataFrame({
        "AppID": [1, 2],
        "Name": ["Short Game", "Long Game"],
        "Playtime_Forever": [0, 0],
        "Average_Playtime": [30, 3000],
        "Genre": ["Action", "RPG"],
        "Tags": ["Arcade", "Story"],
        "status": [GameStatus.LIBRARY, GameStatus.LIBRARY],
        "attention_level": [AttentionLevel.CASUAL, AttentionLevel.FOCUSED],
    })

    with patch("src.api.recommender", GameRecommender(df)):
        response = client.get("/recommend?available_minutes=30&energy=low&context=couch")

    assert response.status_code == 200
    data = response.json()
    assert data["Name"] == "Short Game"

def test_recommend_rejects_invalid_energy(client):
    response = client.get("/recommend?energy=furious")
    assert response.status_code == 422

def test_recommend_rejects_invalid_context(client):
    response = client.get("/recommend?context=bathtub")
    assert response.status_code == 422

def test_recommend_rejects_out_of_range_available_minutes(client):
    assert client.get("/recommend?available_minutes=4").status_code == 422
    assert client.get("/recommend?available_minutes=601").status_code == 422

def test_recommend_with_count_returns_alternates(client):
    df = pd.DataFrame({
        "AppID": [1, 2, 3, 4],
        "Name": ["Game A", "Game B", "Game C", "Game D"],
        "Playtime_Forever": [0, 20, 5, 0],
        "Average_Playtime": [120, 120, 300, 600],
        "Genre": ["Action", "Action", "RPG", "Puzzle"],
        "Tags": ["Indie", "Indie", "Story", "Logic"],
        "status": [GameStatus.LIBRARY, GameStatus.UP_NEXT, GameStatus.PLAYING, GameStatus.LIBRARY],
        "attention_level": [AttentionLevel.UNSET, AttentionLevel.CASUAL, AttentionLevel.FOCUSED, AttentionLevel.UNSET],
    })

    with patch("src.api.recommender", GameRecommender(df)):
        response = client.get("/recommend?count=3")

    assert response.status_code == 200
    data = response.json()
    assert "Name" in data
    assert "score" in data
    assert "reasons" in data
    assert "alternates" in data
    assert len(data["alternates"]) <= 2
    for alt in data["alternates"]:
        assert "Name" in alt
        assert "score" in alt

def test_recommend_default_count_has_no_alternates(client):
    df = pd.DataFrame({
        "AppID": [1, 2],
        "Name": ["Game A", "Game B"],
        "Playtime_Forever": [0, 20],
        "Average_Playtime": [120, 120],
        "Genre": ["Action", "Action"],
        "Tags": ["Indie", "Indie"],
        "status": [GameStatus.LIBRARY, GameStatus.UP_NEXT],
        "attention_level": [AttentionLevel.UNSET, AttentionLevel.CASUAL],
    })

    with patch("src.api.recommender", GameRecommender(df)):
        response = client.get("/recommend?count=1")

    assert response.status_code == 200
    data = response.json()
    assert data["alternates"] == []

@pytest.mark.asyncio
async def test_process_enrichment_persists_rich_metadata(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, genre="Unknown", tags="Unknown"))
        job = EnrichmentJob(total=1)
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    details = {
        "genres": ["Action"],
        "categories": ["Single-player"],
        "header_image": "https://example.com/header.jpg",
        "short_description": "A short Steam description.",
    }
    with patch("src.api.engine", engine), \
         patch("src.api.fetch_game_details", new=AsyncMock(return_value=details)), \
         patch("src.api.fetch_user_tags", new=AsyncMock(return_value=[])), \
         patch("src.api.fetch_time_to_beat", new=AsyncMock(return_value=0)), \
         patch("src.api.asyncio.sleep", new=AsyncMock()), \
         patch("src.api.sync_recommender_with_db"):
        await process_enrichment(job_id=job_id, limit=1)

    with Session(engine) as session:
        game = session.get(Game, 1)
        job = session.get(EnrichmentJob, job_id)
        assert game.genre == "Action"
        assert game.tags == "Single-player"
        assert game.header_image == "https://example.com/header.jpg"
        assert game.short_description == "A short Steam description."
        assert job.status == "completed"
        assert job.total == 1
        assert job.processed == 1
        assert job.succeeded == 1
        assert job.failed == 0

@pytest.mark.asyncio
async def test_enrichment_stores_steamspy_tags(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, genre="Unknown", tags="Unknown"))
        job = EnrichmentJob(total=1)
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    details = {
        "genres": ["Action"],
        "categories": ["Single-player"],
        "header_image": "https://example.com/header.jpg",
        "short_description": "A short Steam description.",
    }
    with patch("src.api.engine", engine), \
         patch("src.api.fetch_game_details", new=AsyncMock(return_value=details)), \
         patch("src.api.fetch_user_tags", new=AsyncMock(return_value=["Roguelike", "Story Rich"])), \
         patch("src.api.fetch_time_to_beat", new=AsyncMock(return_value=0)), \
         patch("src.api.asyncio.sleep", new=AsyncMock()), \
         patch("src.api.sync_recommender_with_db"):
        await process_enrichment(job_id=job_id, limit=1)

    with Session(engine) as session:
        game = session.get(Game, 1)
        assert game.tags == "Roguelike;Story Rich"

def test_enrich_endpoint_returns_job_and_current_progress(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, genre="Unknown", tags="Unknown"))
        session.commit()

    details = {
        "genres": ["Action"],
        "categories": ["Single-player"],
        "header_image": "https://example.com/header.jpg",
        "short_description": "A short Steam description.",
    }
    with patch("src.api.fetch_game_details", new=AsyncMock(return_value=details)), \
         patch("src.api.fetch_user_tags", new=AsyncMock(return_value=[])), \
         patch("src.api.fetch_time_to_beat", new=AsyncMock(return_value=0)), \
         patch("src.api.asyncio.sleep", new=AsyncMock()), \
         patch("src.api.sync_recommender_with_db"):
        response = client.post("/games/enrich?limit=1")

    assert response.status_code == 200
    job_id = response.json()["job_id"]

    response = client.get(f"/games/enrich/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["total"] == 1
    assert data["processed"] == 1
    assert data["succeeded"] == 1
    assert data["failed"] == 0

    response = client.get("/games/enrich/jobs/current")
    assert response.status_code == 200
    assert response.json()["id"] == job_id

def test_current_enrichment_job_prefers_running_then_completed(client):
    with Session(engine) as session:
        failed = EnrichmentJob(status="failed")
        running = EnrichmentJob(status="running")
        completed = EnrichmentJob(status="completed")
        session.add(failed)
        session.add(running)
        session.add(completed)
        session.commit()
        session.refresh(running)
        session.refresh(completed)
        running_id = running.id
        completed_id = completed.id

    response = client.get("/games/enrich/jobs/current")
    assert response.status_code == 200
    assert response.json()["id"] == running_id

    with Session(engine) as session:
        running = session.get(EnrichmentJob, running_id)
        running.status = "failed"
        session.add(running)
        session.commit()

    response = client.get("/games/enrich/jobs/current")
    assert response.status_code == 200
    assert response.json()["id"] == completed_id

def test_lifespan_marks_stale_running_job_failed():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        job = EnrichmentJob(status="running", total=5, processed=1)
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    real_exists = os.path.exists
    with patch("src.api.engine", engine), \
         patch("src.api.os.path.exists", side_effect=lambda path: False if str(path).endswith("sample_library.csv") else real_exists(path)):
        with TestClient(app):
            pass

    with Session(engine) as session:
        job = session.get(EnrichmentJob, job_id)
        assert job.status == "failed"
        assert job.error_summary == "Interrupted by server restart"
    SQLModel.metadata.drop_all(engine)

@pytest.mark.asyncio
async def test_process_enrichment_marks_job_failed_on_crash(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, genre="Unknown", tags="Unknown"))
        job = EnrichmentJob(total=1)
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    with patch("src.api.engine", engine), \
         patch("src.api.enrichment_candidates_query", side_effect=RuntimeError("boom")), \
         patch("src.api.sync_recommender_with_db"):
        await process_enrichment(job_id=job_id, limit=1)

    with Session(engine) as session:
        job = session.get(EnrichmentJob, job_id)
        assert job.status == "failed"
        assert job.error_summary == "boom"
        assert job.completed_at is not None

@pytest.mark.asyncio
async def test_run_scheduled_enrichment_creates_and_runs_job(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, genre="Unknown", tags="Unknown"))
        session.commit()

    with patch("src.api.process_enrichment", new=AsyncMock()) as mock_process:
        await run_scheduled_enrichment()

    with Session(engine) as session:
        jobs = session.exec(select(EnrichmentJob)).all()
        assert len(jobs) == 1
        assert jobs[0].total >= 1
        mock_process.assert_awaited_once_with(jobs[0].id, 50)

@pytest.mark.asyncio
async def test_run_scheduled_enrichment_skips_when_job_running(client):
    with Session(engine) as session:
        session.add(EnrichmentJob(status="running"))
        session.commit()

    with patch("src.api.process_enrichment", new=AsyncMock()) as mock_process:
        await run_scheduled_enrichment()

    with Session(engine) as session:
        jobs = session.exec(select(EnrichmentJob)).all()
        assert len(jobs) == 1
        assert jobs[0].status == "running"
        mock_process.assert_not_awaited()

def test_enrich_endpoint_rejects_concurrent_job(client):
    with Session(engine) as session:
        existing = EnrichmentJob(status="running")
        session.add(existing)
        session.commit()
        session.refresh(existing)
        existing_id = existing.id

    response = client.post("/games/enrich?limit=1")

    assert response.status_code == 200
    assert response.json()["job_id"] == existing_id

    with Session(engine) as session:
        running_jobs = session.exec(
            select(EnrichmentJob).where(EnrichmentJob.status == "running")
        ).all()
        assert len(running_jobs) == 1

def test_current_enrichment_job_returns_failed_when_latest(client):
    with Session(engine) as session:
        completed = EnrichmentJob(status="completed")
        session.add(completed)
        session.commit()
        session.refresh(completed)
        completed.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        session.add(completed)
        session.commit()

        failed = EnrichmentJob(status="failed")
        session.add(failed)
        session.commit()
        session.refresh(failed)
        failed.created_at = datetime(2020, 1, 2, tzinfo=timezone.utc)
        session.add(failed)
        session.commit()
        failed_id = failed.id

    response = client.get("/games/enrich/jobs/current")
    assert response.status_code == 200
    assert response.json()["id"] == failed_id

def csv_file(content: str):
    return {"file": ("library.csv", content, "text/csv")}

def test_upload_preview_reports_changes_without_writing(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Existing", playtime_forever=10, genre="Action", tags="Indie"))
        session.commit()

    csv = "AppID,Name,Playtime_Forever,Genre,Tags\n1,Existing Updated,20,RPG,Story\n2,New Game,0,Action,Arcade\n2,Duplicate New,1,Action,Arcade\n"
    response = client.post("/upload/preview", files=csv_file(csv))

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 3
    assert data["new_games"] == 1
    assert data["updated_games"] == 1
    assert data["duplicate_rows"] == 1
    assert data["duplicate_app_ids"] == [2]

    with Session(engine) as session:
        assert session.get(Game, 2) is None
        assert session.get(Game, 1).name == "Existing"

def test_upload_import_is_collision_safe(client):
    with Session(engine) as session:
        session.add(Game(
            id=1,
            name="Existing",
            playtime_forever=10,
            genre="Action",
            tags="Indie",
            header_image="https://example.com/header.jpg",
            short_description="Keep me",
        ))
        session.commit()

    csv = "AppID,Name,Playtime_Forever,Genre,Tags\n1,Existing Updated,20,Unknown,Unknown\n2,New Game,0,Action,Arcade\n2,Duplicate New,1,Action,Arcade\n"
    response = client.post("/upload", files=csv_file(csv))

    assert response.status_code == 200
    data = response.json()
    assert data["new_games"] == 1
    assert data["updated_games"] == 1
    assert data["duplicate_rows"] == 1
    assert data["games_count"] == 2

    with Session(engine) as session:
        existing = session.get(Game, 1)
        new_game = session.get(Game, 2)
        assert existing.name == "Existing Updated"
        assert existing.playtime_forever == 20
        assert existing.genre == "Action"
        assert existing.tags == "Indie"
        assert existing.header_image == "https://example.com/header.jpg"
        assert existing.short_description == "Keep me"
        assert new_game.name == "New Game"

def test_upload_rolls_back_on_failure(client):
    csv = "AppID,Name,Playtime_Forever\n1,Good Game,0\nnot-an-id,Bad Game,0\n"
    response = client.post("/upload", files=csv_file(csv))

    assert response.status_code == 400
    with Session(engine) as session:
        assert session.exec(select(Game)).all() == []

@pytest.mark.asyncio
async def test_process_enrichment_records_failures(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, genre="Unknown", tags="Unknown"))
        job = EnrichmentJob(total=1)
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    with patch("src.api.engine", engine), \
         patch("src.api.fetch_game_details", new=AsyncMock(return_value=None)), \
         patch("src.api.fetch_time_to_beat", new=AsyncMock(return_value=0)), \
         patch("src.api.asyncio.sleep", new=AsyncMock()), \
         patch("src.api.sync_recommender_with_db"):
        await process_enrichment(job_id=job_id, limit=1)

    with Session(engine) as session:
        job = session.get(EnrichmentJob, job_id)
        assert job.status == "failed"
        assert job.processed == 1
        assert job.succeeded == 0
        assert job.failed == 1
        assert "No Steam details" in job.error_summary

@pytest.mark.asyncio
async def test_process_enrichment_marks_delisted_terminal(client):
    with Session(engine) as session:
        session.add(Game(id=2430, name="Dead App", playtime_forever=0, genre="Unknown", tags="Unknown"))
        job = EnrichmentJob(total=1)
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    with patch("src.api.engine", engine), \
         patch("src.api.fetch_game_details", new=AsyncMock(return_value={})), \
         patch("src.api.fetch_time_to_beat", new=AsyncMock(return_value=0)), \
         patch("src.api.asyncio.sleep", new=AsyncMock()), \
         patch("src.api.sync_recommender_with_db"):
        await process_enrichment(job_id=job_id, limit=1)

    with Session(engine) as session:
        job = session.get(EnrichmentJob, job_id)
        assert job.status == "completed"
        assert job.succeeded == 1
        assert job.failed == 0

        game = session.get(Game, 2430)
        assert game.genre == "Unlisted"
        assert game.header_image == ""
        candidates = session.exec(enrichment_candidates_query(50)).all()
        assert game.id not in [candidate.id for candidate in candidates]

def test_steam_sync_requires_config(client, monkeypatch):
    monkeypatch.delenv("STEAM_API_KEY", raising=False)
    monkeypatch.delenv("STEAM_ID", raising=False)

    response = client.post("/sync/steam")

    assert response.status_code == 503

def test_steam_sync_upserts_and_preserves_user_state(client, monkeypatch):
    monkeypatch.setenv("STEAM_API_KEY", "test-key")
    monkeypatch.setenv("STEAM_ID", "test-steam-id")

    with Session(engine) as session:
        session.add(Game(
            id=10,
            name="Old Game",
            playtime_forever=100,
            status=GameStatus.PLAYING,
            attention_level=AttentionLevel.FOCUSED,
            header_image="http://x/img.jpg",
        ))
        session.commit()

    owned_games = [
        {"appid": 10, "name": "Old Game", "playtime_forever": 200},
        {"appid": 20, "name": "New Game", "playtime_forever": 0},
    ]
    with patch("src.api.fetch_owned_games", new=AsyncMock(return_value=owned_games)), \
         patch("src.api.sync_recommender_with_db"):
        response = client.post("/sync/steam")

    assert response.status_code == 200
    data = response.json()
    assert data["added"] == 1
    assert data["updated"] == 1
    assert data["total"] == 2

    with Session(engine) as session:
        game_10 = session.get(Game, 10)
        assert game_10.playtime_forever == 200
        assert game_10.status == GameStatus.PLAYING
        assert game_10.attention_level == AttentionLevel.FOCUSED
        assert game_10.header_image == "http://x/img.jpg"

        game_20 = session.get(Game, 20)
        assert game_20 is not None
        assert game_20.genre == "Unknown"

def test_steam_sync_handles_steam_failure(client, monkeypatch):
    monkeypatch.setenv("STEAM_API_KEY", "test-key")
    monkeypatch.setenv("STEAM_ID", "test-steam-id")

    with patch("src.api.fetch_owned_games", new=AsyncMock(return_value=None)), \
         patch("src.api.sync_recommender_with_db"):
        response = client.post("/sync/steam")

    assert response.status_code == 502

def test_status_change_logs_play_event(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, status=GameStatus.LIBRARY))
        session.commit()

    response = client.put("/games/1", json={"status": "playing"})
    assert response.status_code == 200

    with Session(engine) as session:
        events = session.exec(select(PlayEvent)).all()
        assert len(events) == 1
        assert events[0].event_type == "status"
        assert events[0].old_value == "library"
        assert events[0].new_value == "playing"

    # Same status again -> no additional event
    response = client.put("/games/1", json={"status": "playing"})
    assert response.status_code == 200

    with Session(engine) as session:
        events = session.exec(select(PlayEvent)).all()
        assert len(events) == 1

def test_steam_sync_logs_playtime_delta(client, monkeypatch):
    monkeypatch.setenv("STEAM_API_KEY", "test-key")
    monkeypatch.setenv("STEAM_ID", "test-steam-id")

    with Session(engine) as session:
        session.add(Game(id=10, name="Old Game", playtime_forever=100, status=GameStatus.PLAYING))
        session.add(Game(id=30, name="Unchanged Game", playtime_forever=50, status=GameStatus.LIBRARY))
        session.commit()

    owned_games = [
        {"appid": 10, "name": "Old Game", "playtime_forever": 250},
        {"appid": 20, "name": "New Game", "playtime_forever": 0},
        {"appid": 30, "name": "Unchanged Game", "playtime_forever": 50},
    ]
    with patch("src.api.fetch_owned_games", new=AsyncMock(return_value=owned_games)), \
         patch("src.api.sync_recommender_with_db"):
        response = client.post("/sync/steam")

    assert response.status_code == 200

    with Session(engine) as session:
        events = session.exec(select(PlayEvent)).all()
        assert len(events) == 1
        assert events[0].game_id == 10
        assert events[0].event_type == "playtime"
        assert events[0].old_value == "100"
        assert events[0].new_value == "250"

def test_activity_stats_endpoint(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=120))
        session.commit()

        now = datetime.now(timezone.utc)
        session.add(PlayEvent(
            game_id=1, event_type="playtime", old_value="0", new_value="120",
            created_at=now,
        ))
        session.add(PlayEvent(
            game_id=1, event_type="status", old_value="playing", new_value="completed",
            created_at=now,
        ))
        session.add(PlayEvent(
            game_id=1, event_type="playtime", old_value="0", new_value="60",
            created_at=now - timedelta(days=10),
        ))
        session.commit()

    response = client.get("/stats/activity")
    assert response.status_code == 200
    data = response.json()
    assert data["minutes_this_week"] == 120
    assert data["finished_this_month"] == 1
    assert len(data["events"]) == 3
    assert data["events"][0]["game_name"] == "Game A"
    # newest-first
    timestamps = [event["created_at"] for event in data["events"]]
    assert timestamps == sorted(timestamps, reverse=True)

def test_enrichment_candidates_include_missing_art(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Missing Art", playtime_forever=0, genre="Action", tags="Indie", header_image=None))
        session.add(Game(id=2, name="Unknown Genre", playtime_forever=0, genre="Unknown", tags="Unknown"))
        session.add(Game(id=3, name="Fully Enriched", playtime_forever=0, genre="Action", tags="Indie", header_image="https://example.com/header.jpg", average_playtime=600))
        session.commit()

    with Session(engine) as session:
        candidates = session.exec(enrichment_candidates_query(50)).all()
        candidate_ids = {game.id for game in candidates}

    assert 1 in candidate_ids
    assert 2 in candidate_ids
    assert 3 not in candidate_ids

@pytest.mark.asyncio
async def test_enrichment_preserves_known_genre(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, genre="Action", tags="Indie", header_image=None))
        job = EnrichmentJob(total=1)
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    details = {
        "genres": ["Casual"],
        "categories": ["Single-player"],
        "header_image": "http://img",
        "short_description": "d",
    }
    with patch("src.api.engine", engine), \
         patch("src.api.fetch_game_details", new=AsyncMock(return_value=details)), \
         patch("src.api.fetch_user_tags", new=AsyncMock(return_value=[])), \
         patch("src.api.fetch_time_to_beat", new=AsyncMock(return_value=0)), \
         patch("src.api.asyncio.sleep", new=AsyncMock()), \
         patch("src.api.sync_recommender_with_db"):
        await process_enrichment(job_id=job_id, limit=1)

    with Session(engine) as session:
        game = session.get(Game, 1)
        assert game.genre == "Action"
        assert game.tags == "Indie"
        assert game.header_image == "http://img"

@pytest.mark.asyncio
async def test_enrichment_fills_time_to_beat(client):
    with Session(engine) as session:
        session.add(Game(
            id=1,
            name="Game A",
            playtime_forever=0,
            genre="Action",
            tags="Indie",
            header_image="http://x",
            average_playtime=None,
        ))
        job = EnrichmentJob(total=1)
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    with patch("src.api.engine", engine), \
         patch("src.api.fetch_game_details", new=AsyncMock(return_value={})), \
         patch("src.api.fetch_time_to_beat", new=AsyncMock(return_value=720)), \
         patch("src.api.asyncio.sleep", new=AsyncMock()), \
         patch("src.api.sync_recommender_with_db"):
        await process_enrichment(job_id=job_id, limit=1)

    with Session(engine) as session:
        game = session.get(Game, 1)
        assert game.average_playtime == 720

def test_sync_interval_helper(monkeypatch):
    monkeypatch.setenv("STEAM_API_KEY", "test-key")
    monkeypatch.setenv("STEAM_ID", "test-steam-id")

    monkeypatch.delenv("SYNC_INTERVAL_HOURS", raising=False)
    assert steam_sync_interval_seconds() == 86400

    monkeypatch.setenv("SYNC_INTERVAL_HOURS", "6")
    assert steam_sync_interval_seconds() == 21600

    monkeypatch.setenv("SYNC_INTERVAL_HOURS", "0")
    assert steam_sync_interval_seconds() is None

    monkeypatch.setenv("SYNC_INTERVAL_HOURS", "garbage")
    assert steam_sync_interval_seconds() is None

    monkeypatch.delenv("STEAM_API_KEY", raising=False)
    monkeypatch.delenv("STEAM_ID", raising=False)
    assert steam_sync_interval_seconds() is None

@pytest.mark.asyncio
async def test_run_steam_sync_callable_directly(client):
    owned_games = [{"appid": 30, "name": "Direct Game", "playtime_forever": 50}]
    with patch("src.api.fetch_owned_games", new=AsyncMock(return_value=owned_games)), \
         patch("src.api.sync_recommender_with_db"):
        with Session(engine) as session:
            result = await run_steam_sync(session)

    assert result["added"] == 1

    with Session(engine) as session:
        game = session.get(Game, 30)
        assert game is not None
        assert game.name == "Direct Game"

def test_create_manual_game(client):
    with patch("src.api.search_game", new=AsyncMock(return_value=None)), \
         patch("src.api.fetch_time_to_beat", new=AsyncMock(return_value=0)), \
         patch("src.api.sync_recommender_with_db"):
        response = client.post("/games", json={"name": "Zelda TOTK", "platform": "switch"})

    assert response.status_code == 200
    data = response.json()
    assert data["id"] >= 1_000_000_000
    assert data["platform"] == "switch"
    assert data["genre"] == "Unknown"
    assert data["playtime_forever"] == 0
    first_id = data["id"]

    with patch("src.api.search_game", new=AsyncMock(return_value=None)), \
         patch("src.api.fetch_time_to_beat", new=AsyncMock(return_value=0)), \
         patch("src.api.sync_recommender_with_db"):
        response = client.post("/games", json={"name": "Another Game", "platform": "switch"})

    assert response.status_code == 200
    assert response.json()["id"] == first_id + 1

def test_create_manual_game_rejects_bad_input(client):
    response = client.post("/games", json={"name": "   ", "platform": "switch"})
    assert response.status_code == 400

    response = client.post("/games", json={"name": "Valid Name", "platform": "steam"})
    assert response.status_code == 400

    with patch("src.api.search_game", new=AsyncMock(return_value=None)), \
         patch("src.api.fetch_time_to_beat", new=AsyncMock(return_value=0)), \
         patch("src.api.sync_recommender_with_db"):
        assert client.post("/games", json={"name": "Hades", "platform": "switch"}).status_code == 200
        response = client.post("/games", json={"name": "hades", "platform": "switch"})
    assert response.status_code == 400
    assert "already in your library" in response.json()["detail"]

def test_create_manual_game_uses_art_lookup(client):
    lookup_result = {"header_image": "http://img", "genres": ["Adventure", "RPG"]}
    with patch("src.api.search_game", new=AsyncMock(return_value=lookup_result)), \
         patch("src.api.fetch_time_to_beat", new=AsyncMock(return_value=0)), \
         patch("src.api.sync_recommender_with_db"):
        response = client.post("/games", json={"name": "Zelda TOTK", "platform": "switch"})

    assert response.status_code == 200
    data = response.json()
    assert data["genre"] == "Adventure;RPG"
    assert data["header_image"] == "http://img"

def test_manual_game_gets_time_to_beat(client):
    with patch("src.api.search_game", new=AsyncMock(return_value=None)), \
         patch("src.api.fetch_time_to_beat", new=AsyncMock(return_value=900)), \
         patch("src.api.sync_recommender_with_db"):
        response = client.post("/games", json={"name": "Hollow Knight", "platform": "switch"})

    assert response.status_code == 200
    assert response.json()["average_playtime"] == 900

def test_enrichment_and_platform_filter_exclude_manual(client):
    with Session(engine) as session:
        session.add(Game(id=1_000_000_000, name="Manual Game", playtime_forever=0, platform="switch", genre="Unknown", header_image=None))
        session.add(Game(id=1, name="Steam Game", playtime_forever=0, genre="Unknown"))
        session.commit()

    with Session(engine) as session:
        candidates = session.exec(enrichment_candidates_query(50)).all()
        candidate_ids = {game.id for game in candidates}

    assert candidate_ids == {1}

    response = client.get("/games?platform=switch")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 1_000_000_000

def test_auto_tag_respects_manual_but_retags_auto(client):
    with Session(engine) as session:
        session.add(Game(
            id=1, name="Game A", playtime_forever=0, genre="Arcade",
            attention_level=AttentionLevel.CASUAL, attention_source="manual",
        ))
        session.add(Game(
            id=2, name="Game B", playtime_forever=0, genre="RPG",
            attention_level=AttentionLevel.CASUAL, attention_source="auto",
        ))
        session.add(Game(
            id=3, name="Game C", playtime_forever=0, genre="Puzzle",
            attention_level=AttentionLevel.UNSET, attention_source=None,
        ))
        session.commit()

    response = client.post("/games/auto-tag")
    assert response.status_code == 200

    with Session(engine) as session:
        game_a = session.get(Game, 1)
        game_b = session.get(Game, 2)
        game_c = session.get(Game, 3)

        assert game_a.attention_level == AttentionLevel.CASUAL
        assert game_a.attention_source == "manual"

        assert game_b.attention_level == AttentionLevel.FOCUSED
        assert game_b.attention_source == "auto"

        assert game_c.attention_level == AttentionLevel.CASUAL
        assert game_c.attention_source == "auto"

def test_automation_stats_empty(client):
    response = client.get("/stats/automation")
    assert response.status_code == 200
    data = response.json()
    assert data["last_sync"] is None
    assert data["last_enrichment"] is None

def test_automation_stats_returns_latest_records(client):
    with Session(engine) as session:
        session.add(SyncRun(success=True, message="Steam sync complete: 1 added, 0 updated."))
        job = EnrichmentJob(total=1, processed=1, succeeded=1, status="completed")
        session.add(job)
        session.commit()

    response = client.get("/stats/automation")
    assert response.status_code == 200
    data = response.json()
    assert data["last_sync"]["success"] is True
    assert data["last_sync"]["message"] == "Steam sync complete: 1 added, 0 updated."
    assert data["last_enrichment"]["status"] == "completed"
    assert data["last_enrichment"]["succeeded"] == 1

def test_steam_sync_records_sync_run(client, monkeypatch):
    monkeypatch.setenv("STEAM_API_KEY", "test-key")
    monkeypatch.setenv("STEAM_ID", "test-steam-id")

    owned_games = [{"appid": 10, "name": "Game", "playtime_forever": 0}]
    with patch("src.api.fetch_owned_games", new=AsyncMock(return_value=owned_games)), \
         patch("src.api.sync_recommender_with_db"):
        response = client.post("/sync/steam")

    assert response.status_code == 200

    with Session(engine) as session:
        runs = session.exec(select(SyncRun)).all()
        assert len(runs) == 1
        assert runs[0].success is True
        assert "Steam sync complete" in runs[0].message

def test_enrichment_candidates_exclude_max_attempts(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Maxed Out", playtime_forever=0, genre="Unknown", enrich_attempts=5))
        session.add(Game(id=2, name="One Left", playtime_forever=0, genre="Unknown", enrich_attempts=4))
        session.commit()

    with Session(engine) as session:
        candidates = session.exec(enrichment_candidates_query(50)).all()
        candidate_ids = {game.id for game in candidates}

    assert 1 not in candidate_ids
    assert 2 in candidate_ids

def test_enrichment_candidates_prioritize_playing_then_queue(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Old Library Game", playtime_forever=0, genre="Unknown", status=GameStatus.LIBRARY))
        session.add(Game(id=2, name="Queued Game", playtime_forever=0, genre="Unknown", status=GameStatus.UP_NEXT))
        session.add(Game(id=3, name="Playing Game", playtime_forever=0, genre="Unknown", status=GameStatus.PLAYING))
        session.commit()

    with Session(engine) as session:
        candidates = session.exec(enrichment_candidates_query(2)).all()
        candidate_ids = [game.id for game in candidates]

    assert candidate_ids == [3, 2]

@pytest.mark.asyncio
async def test_process_enrichment_increments_attempts(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, genre="Unknown", tags="Unknown", header_image=None))
        job = EnrichmentJob(total=1)
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    with patch("src.api.engine", engine), \
         patch("src.api.fetch_game_details", new=AsyncMock(return_value=None)), \
         patch("src.api.fetch_time_to_beat", new=AsyncMock(return_value=0)), \
         patch("src.api.asyncio.sleep", new=AsyncMock()), \
         patch("src.api.sync_recommender_with_db"):
        await process_enrichment(job_id=job_id, limit=1)

    with Session(engine) as session:
        game = session.get(Game, 1)
        assert game.enrich_attempts == 1

def test_enrich_jobs_current_route_not_shadowed_by_game_detail_route(client):
    """Regression: GET /games/{app_id} uses an int converter and must be declared
    after every literal /games/... GET route, or 'enrich' fails int conversion."""
    response = client.get("/games/enrich/jobs/current")
    assert response.status_code == 404
    assert response.json()["detail"] == "No enrichment job found"

def test_get_game_detail_empty_journal(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

    response = client.get("/games/1")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Game A"
    assert data["journal"] == []
    assert data["personal_rating"] is None
    assert data["started_on"] is None
    assert data["completed_on"] is None
    assert data["current_note"] is None

def test_get_game_detail_unknown_game(client):
    response = client.get("/games/999")
    assert response.status_code == 404

def test_get_game_detail_journal_chronological_order(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        session.add(JournalEntry(game_id=1, text="First", created_at=base))
        session.add(JournalEntry(game_id=1, text="Second", created_at=base + timedelta(days=1)))
        session.add(JournalEntry(game_id=1, text="Third", created_at=base + timedelta(days=2)))
        session.commit()

    response = client.get("/games/1")
    assert response.status_code == 200
    texts = [entry["text"] for entry in response.json()["journal"]]
    assert texts == ["First", "Second", "Third"]

def test_journal_entry_crud_happy_path(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

    response = client.post("/games/1/journal", json={"text": "Started the game."})
    assert response.status_code == 200
    entry = response.json()
    assert entry["text"] == "Started the game."
    assert entry["game_id"] == 1
    entry_id = entry["id"]

    response = client.get("/games/1")
    assert [e["text"] for e in response.json()["journal"]] == ["Started the game."]

    response = client.put(f"/games/1/journal/{entry_id}", json={"text": "Updated note."})
    assert response.status_code == 200
    assert response.json()["text"] == "Updated note."

    response = client.get("/games/1")
    assert [e["text"] for e in response.json()["journal"]] == ["Updated note."]

    response = client.delete(f"/games/1/journal/{entry_id}")
    assert response.status_code == 200

    response = client.get("/games/1")
    assert response.json()["journal"] == []

def test_journal_entry_create_blank_text_rejected(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

    response = client.post("/games/1/journal", json={"text": "   "})
    assert response.status_code == 400

def test_journal_entry_create_unknown_game(client):
    response = client.post("/games/999/journal", json={"text": "Hello"})
    assert response.status_code == 404

def test_journal_entry_update_blank_text_rejected(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

    response = client.post("/games/1/journal", json={"text": "Original"})
    entry_id = response.json()["id"]

    response = client.put(f"/games/1/journal/{entry_id}", json={"text": ""})
    assert response.status_code == 400

def test_journal_entry_update_unknown_entry(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

    response = client.put("/games/1/journal/999", json={"text": "Anything"})
    assert response.status_code == 404

def test_journal_entry_update_mismatched_game(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.add(Game(id=2, name="Game B", playtime_forever=0))
        session.commit()

    response = client.post("/games/1/journal", json={"text": "Belongs to game 1"})
    entry_id = response.json()["id"]

    response = client.put(f"/games/2/journal/{entry_id}", json={"text": "Hijack attempt"})
    assert response.status_code == 404

def test_journal_entry_delete_unknown_entry(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

    response = client.delete("/games/1/journal/999")
    assert response.status_code == 404

def test_journal_entry_delete_mismatched_game(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.add(Game(id=2, name="Game B", playtime_forever=0))
        session.commit()

    response = client.post("/games/1/journal", json={"text": "Belongs to game 1"})
    entry_id = response.json()["id"]

    response = client.delete(f"/games/2/journal/{entry_id}")
    assert response.status_code == 404

def test_update_game_sets_personal_context(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

    response = client.put("/games/1", json={
        "personal_rating": 5,
        "started_on": "2026-01-01",
        "completed_on": "2026-02-01",
        "current_note": "Left off at the final dungeon.",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["personal_rating"] == 5
    assert data["started_on"] == "2026-01-01"
    assert data["completed_on"] == "2026-02-01"
    assert data["current_note"] == "Left off at the final dungeon."

    with Session(engine) as session:
        game = session.get(Game, 1)
        assert game.personal_rating == 5
        assert game.current_note == "Left off at the final dungeon."

def test_update_game_rejects_out_of_range_rating(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

    assert client.put("/games/1", json={"personal_rating": 0}).status_code == 422
    assert client.put("/games/1", json={"personal_rating": 6}).status_code == 422

def test_update_game_rejects_invalid_date(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

    response = client.put("/games/1", json={"started_on": "not-a-date"})
    assert response.status_code == 422

def test_delete_game_removes_journal_entries(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

    client.post("/games/1/journal", json={"text": "Some note."})

    response = client.delete("/games/1")
    assert response.status_code == 200

    with Session(engine) as session:
        entries = session.exec(select(JournalEntry).where(JournalEntry.game_id == 1)).all()
        assert entries == []

def test_create_recommendation_decision_accepted_play(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, tags="Indie;Story", status=GameStatus.LIBRARY))
        session.commit()

    response = client.post("/recommendations/decisions", json={"game_id": 1, "decision": "accepted_play"})
    assert response.status_code == 200
    data = response.json()
    assert data["game_id"] == 1
    assert data["decision"] == "accepted_play"
    assert data["reason"] is None
    assert data["tags_snapshot"] == "Indie;Story"

    # Recording a decision does not mutate game status
    with Session(engine) as session:
        game = session.get(Game, 1)
        assert game.status == GameStatus.LIBRARY

def test_create_recommendation_decision_rejected_with_reason(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0, tags="Indie"))
        session.commit()

    response = client.post("/recommendations/decisions", json={
        "game_id": 1,
        "decision": "rejected",
        "reason": "too_long",
        "mood": "story_night",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "rejected"
    assert data["reason"] == "too_long"
    assert data["mood"] == "story_night"

def test_create_recommendation_decision_deferred(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

    response = client.post("/recommendations/decisions", json={
        "game_id": 1,
        "decision": "deferred",
        "reason": "defer_for_now",
    })
    assert response.status_code == 200
    assert response.json()["decision"] == "deferred"

def test_create_recommendation_decision_unknown_game(client):
    response = client.post("/recommendations/decisions", json={"game_id": 999, "decision": "accepted_play"})
    assert response.status_code == 404

def test_create_recommendation_decision_invalid_decision_value(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

    response = client.post("/recommendations/decisions", json={"game_id": 1, "decision": "maybe_later"})
    assert response.status_code == 422

def test_create_recommendation_decision_invalid_reason_value(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

    response = client.post("/recommendations/decisions", json={
        "game_id": 1,
        "decision": "rejected",
        "reason": "just_because",
    })
    assert response.status_code == 422

def test_list_recommendation_decisions_returns_newest_first(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.add(Game(id=2, name="Game B", playtime_forever=0))
        session.commit()

    client.post("/recommendations/decisions", json={"game_id": 1, "decision": "accepted_play"})
    client.post("/recommendations/decisions", json={"game_id": 2, "decision": "rejected", "reason": "too_long"})

    response = client.get("/recommendations/decisions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["game_id"] == 2
    assert data[1]["game_id"] == 1

def test_delete_recommendation_decisions_clears_all(client):
    with Session(engine) as session:
        session.add(Game(id=1, name="Game A", playtime_forever=0))
        session.commit()

    client.post("/recommendations/decisions", json={"game_id": 1, "decision": "accepted_play"})
    client.post("/recommendations/decisions", json={"game_id": 1, "decision": "deferred"})

    response = client.delete("/recommendations/decisions")
    assert response.status_code == 200
    assert response.json() == {"cleared": 2}

    with Session(engine) as session:
        remaining = session.exec(select(RecommendationDecision)).all()
        assert remaining == []
