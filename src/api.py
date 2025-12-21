from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
import os
import shutil
import pandas as pd
from typing import Optional, List
from sqlmodel import Session, select, col

from src.data_loader import load_steam_library
from src.recommender import GameRecommender
from src.database import init_db, engine, get_session
from src.models import Game, GameStatus, AttentionLevel, GameUpdate

# Global recommender instance
recommender = None

def sync_recommender_with_db():
    """Load data from database into the global recommender instance."""
    global recommender
    with Session(engine) as session:
        statement = select(Game)
        results = session.exec(statement).all()
        if results:
            data = [game.model_dump() for game in results]
            df = pd.DataFrame(data)
            df = df.rename(columns={
                'id': 'AppID',
                'name': 'Name',
                'playtime_forever': 'Playtime_Forever',
                'genre': 'Genre',
                'tags': 'Tags'
            })
            if 'Average_Playtime' not in df.columns:
                df['Average_Playtime'] = 0
            
            recommender = GameRecommender(df)
            print(f"Recommender synced with DB. Total games: {len(df)}")
        else:
            recommender = GameRecommender(pd.DataFrame())
            print("Recommender initialized with empty data (DB is empty).")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    init_db()
    
    with Session(engine) as session:
        count = session.exec(select(Game)).all()
        if not count:
            print("DB is empty. Attempting to load sample data...")
            sample_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_library.csv')
            if os.path.exists(sample_path):
                try:
                    df = load_steam_library(sample_path)
                    for _, row in df.iterrows():
                        game = Game(
                            id=int(row['AppID']),
                            name=str(row['Name']),
                            playtime_forever=int(row['Playtime_Forever']),
                            genre=str(row.get('Genre', 'Unknown')),
                            tags=str(row.get('Tags', 'Unknown')),
                            status=GameStatus.LIBRARY,
                            attention_level=AttentionLevel.UNSET
                        )
                        session.add(game)
                    session.commit()
                    print(f"Loaded {len(df)} games from {sample_path} into DB.")
                except Exception as e:
                    print(f"Error loading sample data: {e}")
            else:
                print(f"Warning: Sample data not found at {sample_path}")
    
    sync_recommender_with_db()
    yield
    print("Shutting down...")

app = FastAPI(
    title="GameButler API",
    description="API for recommending Steam games.",
    version="0.2.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RecommendationResponse(BaseModel):
    AppID: int
    Name: str
    Playtime_Forever: int
    Genre: str
    Tags: str
    Average_Playtime: Optional[int] = None
    status: Optional[str] = None
    attention_level: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Welcome to GameButler API! Visit /docs for API documentation."}

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "GameButler API is running."}

@app.get("/games", response_model=List[Game])
async def list_games(
    status: Optional[GameStatus] = None,
    attention_level: Optional[AttentionLevel] = None,
    search: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    List games with optional filtering.
    """
    query = select(Game)
    if status:
        query = query.where(Game.status == status)
    if attention_level:
        query = query.where(Game.attention_level == attention_level)
    if search:
        query = query.where(col(Game.name).contains(search))
        
    results = session.exec(query).all()
    return results

@app.put("/games/{app_id}", response_model=Game)
async def update_game(
    app_id: int, 
    game_update: GameUpdate, 
    session: Session = Depends(get_session)
):
    """
    Update a game's status or attention level.
    """
    game = session.get(Game, app_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
        
    game_data = game_update.model_dump(exclude_unset=True)
    for key, value in game_data.items():
        setattr(game, key, value)
        
    session.add(game)
    session.commit()
    session.refresh(game)
    
    # Sync Recommender (Optimizable later to not reload everything)
    sync_recommender_with_db()
    
    return game

@app.post("/upload")
async def upload_library(file: UploadFile = File(...), session: Session = Depends(get_session)):
    """
    Upload a new Steam library CSV file and save to the database.
    """
    temp_file_path = f"temp_{file.filename}"
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        df = load_steam_library(temp_file_path)
        
        for _, row in df.iterrows():
            app_id = int(row['AppID'])
            existing_game = session.get(Game, app_id)
            if existing_game:
                existing_game.name = str(row['Name'])
                existing_game.playtime_forever = int(row['Playtime_Forever'])
                existing_game.genre = str(row.get('Genre', 'Unknown'))
                existing_game.tags = str(row.get('Tags', 'Unknown'))
                session.add(existing_game)
            else:
                game = Game(
                    id=app_id,
                    name=str(row['Name']),
                    playtime_forever=int(row['Playtime_Forever']),
                    genre=str(row.get('Genre', 'Unknown')),
                    tags=str(row.get('Tags', 'Unknown')),
                    status=GameStatus.LIBRARY,
                    attention_level=AttentionLevel.UNSET
                )
                session.add(game)
        
        session.commit()
        sync_recommender_with_db()
        os.remove(temp_file_path)
        
        return {"message": f"Successfully loaded library from {file.filename}", "games_count": len(recommender.df)}
        
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")

@app.get("/recommend", response_model=RecommendationResponse)
async def recommend_game(
    genre: Optional[str] = None,
    tag: Optional[str] = None,
    unplayed_only: bool = False,
    length: Optional[str] = Query(None, pattern="^(short|medium|long)$"),
    attention_level: Optional[str] = Query(None, pattern="^(casual|focused)$")
):
    """
    Get a game recommendation based on filters.
    """
    if recommender is None or recommender.df.empty:
        raise HTTPException(status_code=404, detail="No game library loaded. Please upload a CSV file.")

    min_len = None
    max_len = None
    
    if length == 'short':
        max_len = 300
    elif length == 'long':
        min_len = 1200
    elif length == 'medium':
        min_len = 300
        max_len = 1200
        
    game = recommender.recommend(
        genre=genre,
        tag=tag,
        unplayed_only=unplayed_only,
        min_length=min_len,
        max_length=max_len,
        attention_level=attention_level
    )
    
    if game is None:
        raise HTTPException(status_code=404, detail="No suitable game found matching your criteria.")
        
    return game.to_dict()

if __name__ == "__main__":
    print("Starting Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
