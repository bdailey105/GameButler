from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from src.api import app, get_session
from src.models import Game, GameStatus, AttentionLevel
import pytest
from unittest.mock import patch

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
    SQLModel.metadata.create_all(engine)
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