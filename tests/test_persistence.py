import pytest
import os
from sqlmodel import Session, select, create_engine, SQLModel
from src.models import Game, GameStatus, AttentionLevel
from src.recommender import GameRecommender
import pandas as pd

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
