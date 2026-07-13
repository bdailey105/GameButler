from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
import os
import shutil
import pandas as pd
import asyncio
import re
import tempfile
from typing import Optional, List, Literal
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select, col, or_
from sqlalchemy import case

from src.data_loader import load_steam_library, load_external_library, EXTERNAL_VALID_PLATFORMS
from src.recommender import GameRecommender, _format_hours
from src.database import init_db, engine, get_session
from src.models import Game, GameStatus, AttentionLevel, GameUpdate, EnrichmentJob, QueueReorder, BulkGameUpdate, PlayEvent, SyncRun, JournalEntry, RecommendationDecision
from src.logic import apply_attention_heuristics
from src.steam_client import fetch_game_details, fetch_owned_games
from src.steamspy_client import fetch_user_tags
from src.steamgriddb_client import search_game
from src.hltb_client import fetch_time_to_beat

# Global recommender instance
recommender = None

def utc_now():
    return datetime.now(timezone.utc)

def as_naive_utc(dt: datetime) -> datetime:
    """Datetimes round-trip through SQLite as naive UTC; normalize aware values too."""
    return dt.replace(tzinfo=None) if dt.tzinfo else dt

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
                'tags': 'Tags',
                'average_playtime': 'Average_Playtime'
            })
            if 'Average_Playtime' not in df.columns:
                df['Average_Playtime'] = 0
            df['Average_Playtime'] = df['Average_Playtime'].fillna(0)

            games_by_id = {game.id: game for game in results}
            cutoff = as_naive_utc(utc_now() - timedelta(days=30))
            decisions = session.exec(
                select(RecommendationDecision).where(RecommendationDecision.created_at >= cutoff)
            ).all()
            feedback = []
            for decision in decisions:
                game = games_by_id.get(decision.game_id)
                feedback.append({
                    "game_id": decision.game_id,
                    "decision": decision.decision,
                    "reason": decision.reason,
                    "tags_snapshot": decision.tags_snapshot,
                    "game_name": game.name if game else None,
                    "created_at": decision.created_at,
                })

            recommender = GameRecommender(df, feedback=feedback)
            print(f"Recommender synced with DB. Total games: {len(df)}")
        else:
            recommender = GameRecommender(pd.DataFrame())
            print("Recommender initialized with empty data (DB is empty).")

def estimate_remaining(game) -> Optional[dict]:
    """Metadata-derived remaining-time estimate. Never a completion tracker.
    Returns None when average_playtime is missing/zero or implausible
    (avoid inventing numbers). playtime >= average -> beyond_typical."""
    average = game.average_playtime
    if average is None or average <= 0:
        return None

    if game.playtime_forever >= average:
        return {
            "minutes": 0,
            "confidence": "beyond_typical",
            "label": "Playtime already exceeds the typical time to beat",
        }

    minutes = average - game.playtime_forever
    return {
        "minutes": minutes,
        "confidence": "rough_estimate",
        "label": f"~{_format_hours(minutes)} left — rough estimate from HowLongToBeat, not actual progress",
    }

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
                        apply_attention_heuristics(game)
                        session.add(game)
                    session.commit()
                    print(f"Loaded {len(df)} games from {sample_path} into DB.")
                except Exception as e:
                    print(f"Error loading sample data: {e}")
            else:
                print(f"Warning: Sample data not found at {sample_path}")
    
    sync_recommender_with_db()

    with Session(engine) as session:
        stale_jobs = session.exec(
            select(EnrichmentJob).where(EnrichmentJob.status == "running")
        ).all()
        for stale_job in stale_jobs:
            # Background tasks die with the process — a "running" job at boot is a
            # zombie that would block enrichment forever
            stale_job.status = "failed"
            stale_job.error_summary = "Interrupted by server restart"
            stale_job.completed_at = utc_now()
            stale_job.updated_at = stale_job.completed_at
            session.add(stale_job)
        if stale_jobs:
            session.commit()
            print(f"Marked {len(stale_jobs)} interrupted enrichment job(s) as failed.")

    task = None
    interval = steam_sync_interval_seconds()
    if interval is not None:
        task = asyncio.create_task(steam_sync_scheduler())
    else:
        print("Steam auto-sync disabled (no credentials or SYNC_INTERVAL_HOURS=0).")

    yield
    if task is not None:
        task.cancel()
    print("Shutting down...")

app = FastAPI(
    title="GameButler API",
    description="API for recommending Steam games.",
    version="0.4.0",
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
    header_image: Optional[str] = None
    short_description: Optional[str] = None
    status: Optional[str] = None
    attention_level: Optional[str] = None
    score: Optional[int] = None
    reasons: List[str] = []
    alternates: List["RecommendationResponse"] = []

RecommendationResponse.model_rebuild()

class ImportPreviewResponse(BaseModel):
    filename: str
    total_rows: int
    new_games: int
    updated_games: int
    unchanged_games: int
    duplicate_rows: int
    duplicate_app_ids: List[int] = []

class ExternalImportInvalidRow(BaseModel):
    row: int
    error: str

class ExternalImportPreviewResponse(BaseModel):
    filename: str
    total_rows: int
    new: int
    updated: int
    skipped: int
    duplicates: int
    invalid: List[ExternalImportInvalidRow] = []

class ExternalImportResponse(BaseModel):
    imported: int
    updated: int
    skipped: int
    duplicates: int
    invalid: List[ExternalImportInvalidRow] = []

# Steam AppIDs are far below this; manual/non-Steam games are allocated ids
# from this floor upward, so collisions with Steam sync/CSV import are impossible.
MANUAL_ID_FLOOR = 1_000_000_000

class ManualGameCreate(BaseModel):
    name: str
    platform: str
    genre: Optional[str] = None
    attention_level: Optional[AttentionLevel] = None

class JournalEntryCreate(BaseModel):
    text: str

DecisionType = Literal[
    "accepted_play",
    "accepted_queue",
    "rejected",
    "deferred",
    "more_like_this",
    "less_like_this",
]
DecisionReason = Literal[
    "not_in_the_mood",
    "too_long",
    "too_demanding",
    "bounced_off",
    "defer_for_now",
]

class RecommendationDecisionCreate(BaseModel):
    game_id: int
    decision: DecisionType
    reason: Optional[DecisionReason] = None
    mood: Optional[str] = None

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
    platform: Optional[str] = None,
    played: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    query = select(Game)
    if status:
        query = query.where(Game.status == status)
    if attention_level:
        query = query.where(Game.attention_level == attention_level)
    if search:
        query = query.where(col(Game.name).contains(search))
    if platform:
        query = query.where(Game.platform == platform)
    if played is not None:
        query = query.where(Game.playtime_forever > 0 if played else Game.playtime_forever == 0)

    results = session.exec(query).all()
    if status == GameStatus.UP_NEXT:
        results = sorted(results, key=lambda game: (game.queue_position is None, game.queue_position or 0, game.name.lower()))
    return results

@app.post("/games", response_model=Game)
async def create_game(payload: ManualGameCreate, session: Session = Depends(get_session)):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    if payload.platform == "steam":
        raise HTTPException(status_code=400, detail="Steam games come from sync/CSV import")

    duplicate = session.exec(
        select(Game).where(
            Game.platform == payload.platform,
            col(Game.name).ilike(payload.name.strip()),
        )
    ).first()
    if duplicate:
        raise HTTPException(status_code=400, detail=f"'{duplicate.name}' is already in your library")

    existing_ids = session.exec(
        select(Game.id).where(Game.id >= MANUAL_ID_FLOOR)
    ).all()
    next_id = max(existing_ids, default=MANUAL_ID_FLOOR - 1) + 1

    lookup = await search_game(payload.name)

    genre = payload.genre
    header_image = None
    if lookup:
        header_image = lookup.get("header_image")
        if not genre and lookup.get("genres"):
            genre = ";".join(lookup["genres"])

    game = Game(
        id=next_id,
        name=payload.name.strip(),
        platform=payload.platform,
        genre=genre or "Unknown",
        tags="Unknown",
        playtime_forever=0,
        status=GameStatus.LIBRARY,
        attention_level=payload.attention_level or AttentionLevel.UNSET,
        header_image=header_image,
    )
    if payload.attention_level is None:
        apply_attention_heuristics(game)

    game.average_playtime = await fetch_time_to_beat(payload.name.strip())

    session.add(game)
    session.commit()
    session.refresh(game)
    sync_recommender_with_db()
    return game

@app.put("/games/queue", response_model=List[Game])
async def reorder_queue(
    reorder: QueueReorder,
    session: Session = Depends(get_session),
):
    if len(reorder.app_ids) != len(set(reorder.app_ids)):
        raise HTTPException(status_code=400, detail="Queue order contains duplicate game ids")

    queued_games = session.exec(select(Game).where(Game.status == GameStatus.UP_NEXT)).all()
    queued_by_id = {game.id: game for game in queued_games}
    missing = [app_id for app_id in reorder.app_ids if app_id not in queued_by_id]
    if missing:
        raise HTTPException(status_code=400, detail=f"Not queued: {missing[0]}")
    omitted = [game.id for game in queued_games if game.id not in set(reorder.app_ids)]
    if omitted:
        raise HTTPException(status_code=400, detail=f"Missing queued game: {omitted[0]}")

    for position, app_id in enumerate(reorder.app_ids, start=1):
        queued_by_id[app_id].queue_position = position
        session.add(queued_by_id[app_id])

    session.commit()
    sync_recommender_with_db()
    return sorted(queued_games, key=lambda game: game.queue_position or 0)

@app.put("/games/bulk")
async def bulk_update_games(
    payload: BulkGameUpdate,
    session: Session = Depends(get_session),
):
    if not payload.app_ids:
        raise HTTPException(status_code=400, detail="app_ids cannot be empty")
    if len(payload.app_ids) != len(set(payload.app_ids)):
        raise HTTPException(status_code=400, detail="app_ids contains duplicates")

    update_data = payload.model_dump(exclude_unset=True, exclude={"app_ids"})
    if not update_data:
        raise HTTPException(status_code=400, detail="No updatable field provided")

    games_by_id = {
        game.id: game
        for game in session.exec(select(Game).where(col(Game.id).in_(payload.app_ids))).all()
    }
    missing = [app_id for app_id in payload.app_ids if app_id not in games_by_id]
    if missing:
        raise HTTPException(status_code=404, detail=f"Games not found: {missing}")

    new_status = update_data.get("status")
    attention_provided = "attention_level" in update_data
    new_attention = update_data.get("attention_level")
    session_tags_provided = "session_tags" in update_data
    new_session_tags = update_data.get("session_tags")

    next_queue_position = None
    if new_status == GameStatus.UP_NEXT:
        positions = session.exec(
            select(Game.queue_position).where(Game.status == GameStatus.UP_NEXT)
        ).all()
        next_queue_position = max([position or 0 for position in positions], default=0) + 1

    updated_count = 0
    for app_id in payload.app_ids:
        game = games_by_id[app_id]
        modified = False

        if new_status is not None and new_status != game.status:
            old_status = game.status
            game.status = new_status
            if new_status == GameStatus.UP_NEXT:
                game.queue_position = next_queue_position
                next_queue_position += 1
            else:
                game.queue_position = None
            session.add(PlayEvent(game_id=game.id, event_type="status", old_value=old_status.value, new_value=new_status.value))
            modified = True

        if attention_provided and new_attention != game.attention_level:
            game.attention_level = new_attention
            game.attention_source = None if new_attention == AttentionLevel.UNSET else "manual"
            modified = True

        if session_tags_provided and new_session_tags != game.session_tags:
            game.session_tags = new_session_tags
            modified = True

        if modified:
            session.add(game)
            updated_count += 1

    session.commit()
    sync_recommender_with_db()
    return {"updated": updated_count}

@app.put("/games/{app_id}", response_model=Game)
async def update_game(
    app_id: int, 
    game_update: GameUpdate, 
    session: Session = Depends(get_session)
):
    game = session.get(Game, app_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
        
    game_data = game_update.model_dump(exclude_unset=True)
    new_status = game_data.get("status")
    if new_status == GameStatus.UP_NEXT and game.status != GameStatus.UP_NEXT:
        positions = session.exec(
            select(Game.queue_position).where(Game.status == GameStatus.UP_NEXT)
        ).all()
        game.queue_position = max([position or 0 for position in positions], default=0) + 1
    elif new_status and new_status != GameStatus.UP_NEXT:
        game.queue_position = None

    old_status = game.status

    for key, value in game_data.items():
        if key == "queue_position":
            continue
        setattr(game, key, value)

    if "attention_level" in game_data:
        game.attention_source = None if game.attention_level == AttentionLevel.UNSET else "manual"

    if new_status and new_status != old_status:
        session.add(PlayEvent(game_id=game.id, event_type="status", old_value=old_status.value, new_value=new_status.value))

    session.add(game)
    session.commit()
    session.refresh(game)
    sync_recommender_with_db()
    return game

@app.delete("/games/{app_id}")
async def delete_game(app_id: int, session: Session = Depends(get_session)):
    game = session.get(Game, app_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    events = session.exec(select(PlayEvent).where(PlayEvent.game_id == app_id)).all()
    for event in events:
        session.delete(event)
    entries = session.exec(select(JournalEntry).where(JournalEntry.game_id == app_id)).all()
    for entry in entries:
        session.delete(entry)
    session.delete(game)
    session.commit()
    sync_recommender_with_db()
    return {"message": f"Deleted {game.name}."}

@app.post("/games/auto-tag")
async def auto_tag_games(session: Session = Depends(get_session)):
    # Manual overrides are permanent; everything else (never tagged, or previously
    # auto-tagged) is fair game for re-running the heuristics.
    statement = select(Game).where(
        or_(col(Game.attention_source) != "manual", col(Game.attention_source).is_(None))
    )
    games = session.exec(statement).all()

    count = 0
    for game in games:
        original_level = game.attention_level
        game.attention_level = AttentionLevel.UNSET
        apply_attention_heuristics(game)
        if game.attention_level != AttentionLevel.UNSET and game.attention_level != original_level:
            session.add(game)
            count += 1

    session.commit()
    sync_recommender_with_db()
    return {"message": f"Successfully auto-tagged {count} games."}

# ponytail: hard cap, no manual-retry override yet — bump attempts to 0 in DB to force retry
MAX_ENRICH_ATTEMPTS = 5

def enrichment_candidates_query(limit: int):
    # Games the user is actually playing get enriched first, then the queue,
    # then the rest of the library — not whatever happens to have the lowest id
    status_priority = case(
        (Game.status == GameStatus.PLAYING, 0),
        (Game.status == GameStatus.UP_NEXT, 1),
        else_=2,
    )
    return select(Game).where(
        ((Game.genre == "Unknown") | (Game.tags == "Unknown") | (Game.header_image == None) | (Game.average_playtime == None))  # noqa: E711
        & (Game.platform == "steam")
        & (Game.enrich_attempts < MAX_ENRICH_ATTEMPTS)
    ).order_by(status_priority, col(Game.id)).limit(limit)

PER_GAME_TIMEOUT = 120.0

async def process_enrichment(job_id: int, limit: int):
    """Background task to enrich games."""
    print(f"Starting enrichment task for {limit} games...")
    with Session(engine) as session:
        job = session.get(EnrichmentJob, job_id)
        if not job:
            print(f"Enrichment job {job_id} not found.")
            return

        try:
            games_to_enrich = session.exec(enrichment_candidates_query(limit)).all()
            job.total = len(games_to_enrich)
            job.updated_at = utc_now()
            session.add(job)
            session.commit()
            print(f"Found {len(games_to_enrich)} games to enrich.")

            saved_metadata = 0

            async def enrich_one(game):
                nonlocal saved_metadata
                details = await fetch_game_details(game.id)

                if details:
                    if game.genre == "Unknown" and details.get("genres"):
                        game.genre = ";".join(details["genres"])
                    if game.tags == "Unknown" and details.get("categories"):
                        game.tags = ";".join(details["categories"])
                    # "" = checked, Steam has no art (keeps game out of future candidate runs)
                    game.header_image = details.get("header_image") or game.header_image or ""
                    game.short_description = details.get("short_description") or game.short_description

                    user_tags = await fetch_user_tags(game.id)
                    if user_tags:
                        game.tags = ";".join(user_tags)

                    session.add(game)
                    job.succeeded += 1
                    saved_metadata += 1
                elif details == {}:
                    # Steam has no store page (delisted/legacy) — mark terminal so the
                    # game drops out of future candidate runs instead of failing forever
                    if game.genre == "Unknown":
                        game.genre = "Unlisted"
                    if game.tags == "Unknown":
                        game.tags = ""
                    if game.header_image is None:
                        game.header_image = ""
                    session.add(game)
                    job.succeeded += 1
                else:
                    job.failed += 1
                    job.error_summary = f"No Steam details for {game.id}"

                if game.average_playtime is None:
                    ttb = await fetch_time_to_beat(game.name)
                    if ttb is not None:
                        game.average_playtime = ttb
                        session.add(game)

            for game in games_to_enrich:
                try:
                    print(f"Fetching details for {game.name} ({game.id})...")
                    await asyncio.wait_for(enrich_one(game), timeout=PER_GAME_TIMEOUT)

                    # Respect rate limits
                    await asyncio.sleep(1.5)

                except Exception as e:
                    print(f"Error enriching {game.id}: {e}")
                    job.failed += 1
                    job.error_summary = str(e)
                finally:
                    job.processed += 1
                    job.updated_at = utc_now()
                    session.add(job)
                    game.enrich_attempts += 1
                    session.add(game)
                    session.commit()

            job.status = "failed" if job.failed else "completed"
            job.completed_at = utc_now()
            job.updated_at = job.completed_at
            session.add(job)
            session.commit()
            print(f"Enrichment complete. Processed {job.processed} games.")
            if saved_metadata > 0:
                sync_recommender_with_db()
        except Exception as e:
            print(f"Enrichment job {job_id} crashed: {e}")
            job.status = "failed"
            job.error_summary = str(e)
            job.completed_at = utc_now()
            job.updated_at = job.completed_at
            session.add(job)
            session.commit()

@app.post("/games/enrich")
async def enrich_games(
    background_tasks: BackgroundTasks,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """
    Trigger a background job to fetch metadata from Steam for games with missing info.
    """
    existing = session.exec(
        select(EnrichmentJob).where(EnrichmentJob.status == "running")
    ).first()
    if existing:
        return {"job_id": existing.id, "message": "Enrichment already in progress."}

    total = len(session.exec(enrichment_candidates_query(limit)).all())
    job = EnrichmentJob(total=total)
    session.add(job)
    session.commit()
    session.refresh(job)
    background_tasks.add_task(process_enrichment, job.id, limit)
    return {"job_id": job.id, "message": f"Enrichment started for up to {limit} games. This may take a while."}

@app.get("/games/enrich/jobs/current", response_model=EnrichmentJob)
async def current_enrichment_job(session: Session = Depends(get_session)):
    job = session.exec(
        select(EnrichmentJob)
        .where(EnrichmentJob.status == "running")
        .order_by(EnrichmentJob.created_at.desc())
    ).first()
    if not job:
        job = session.exec(
            select(EnrichmentJob)
            .order_by(EnrichmentJob.created_at.desc())
        ).first()
    if not job:
        raise HTTPException(status_code=404, detail="No enrichment job found")
    return job

@app.get("/games/enrich/jobs/{job_id}", response_model=EnrichmentJob)
async def get_enrichment_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(EnrichmentJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Enrichment job not found")
    return job

# NOTE: this must stay below every literal "/games/..." GET route above — the int
# converter on {app_id} would otherwise swallow paths like /games/enrich/jobs/current.
@app.get("/games/{app_id}")
async def get_game(app_id: int, session: Session = Depends(get_session)):
    game = session.get(Game, app_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    entries = session.exec(
        select(JournalEntry)
        .where(JournalEntry.game_id == app_id)
        .order_by(JournalEntry.created_at, JournalEntry.id)
    ).all()

    result = game.model_dump()
    result["journal"] = [entry.model_dump() for entry in entries]
    result["remaining_estimate"] = estimate_remaining(game)
    return result

@app.post("/games/{app_id}/journal", response_model=JournalEntry)
async def create_journal_entry(
    app_id: int,
    payload: JournalEntryCreate,
    session: Session = Depends(get_session),
):
    game = session.get(Game, app_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Journal entry text cannot be empty")

    entry = JournalEntry(game_id=app_id, text=payload.text.strip())
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry

@app.put("/games/{app_id}/journal/{entry_id}", response_model=JournalEntry)
async def update_journal_entry(
    app_id: int,
    entry_id: int,
    payload: JournalEntryCreate,
    session: Session = Depends(get_session),
):
    entry = session.get(JournalEntry, entry_id)
    if not entry or entry.game_id != app_id:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Journal entry text cannot be empty")

    entry.text = payload.text.strip()
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry

@app.delete("/games/{app_id}/journal/{entry_id}")
async def delete_journal_entry(
    app_id: int,
    entry_id: int,
    session: Session = Depends(get_session),
):
    entry = session.get(JournalEntry, entry_id)
    if not entry or entry.game_id != app_id:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    session.delete(entry)
    session.commit()
    return {"message": "Journal entry deleted."}

@app.get("/stats/activity")
async def activity_stats(limit: int = 20, session: Session = Depends(get_session)):
    week_ago = as_naive_utc(utc_now() - timedelta(days=7))
    month_ago = as_naive_utc(utc_now() - timedelta(days=30))

    playtime_events = session.exec(
        select(PlayEvent).where(PlayEvent.event_type == "playtime")
    ).all()
    minutes_this_week = sum(
        int(event.new_value) - int(event.old_value)
        for event in playtime_events
        if as_naive_utc(event.created_at) >= week_ago
    )

    status_events = session.exec(
        select(PlayEvent).where(PlayEvent.event_type == "status")
    ).all()
    started_this_month = sum(
        1 for event in status_events
        if event.new_value == "playing" and as_naive_utc(event.created_at) >= month_ago
    )
    finished_this_month = sum(
        1 for event in status_events
        if event.new_value == "completed" and as_naive_utc(event.created_at) >= month_ago
    )

    recent_events = session.exec(
        select(PlayEvent).order_by(PlayEvent.created_at.desc()).limit(limit)
    ).all()
    events = []
    for event in recent_events:
        game = session.get(Game, event.game_id)
        events.append({
            "id": event.id,
            "game_id": event.game_id,
            "game_name": game.name if game else None,
            "header_image": game.header_image if game else None,
            "event_type": event.event_type,
            "old_value": event.old_value,
            "new_value": event.new_value,
            # stored naive UTC; mark aware so clients parse it as UTC, not local
            "created_at": event.created_at.replace(tzinfo=timezone.utc) if event.created_at.tzinfo is None else event.created_at,
        })

    return {
        "minutes_this_week": minutes_this_week,
        "started_this_month": started_this_month,
        "finished_this_month": finished_this_month,
        "events": events,
    }

@app.get("/stats/automation")
async def automation_stats(session: Session = Depends(get_session)):
    last_sync = session.exec(
        select(SyncRun).order_by(SyncRun.finished_at.desc())
    ).first()
    last_enrichment = session.exec(
        select(EnrichmentJob).order_by(EnrichmentJob.created_at.desc())
    ).first()

    return {
        "last_sync": last_sync.model_dump() if last_sync else None,
        "last_enrichment": last_enrichment.model_dump() if last_enrichment else None,
    }

def preview_import(df: pd.DataFrame, session: Session, filename: str) -> ImportPreviewResponse:
    app_ids = [int(app_id) for app_id in df["AppID"]]
    duplicate_app_ids = sorted({app_id for app_id in app_ids if app_ids.count(app_id) > 1})
    unique_ids = set()
    new_games = 0
    updated_games = 0

    for app_id in app_ids:
        if app_id in unique_ids:
            continue
        unique_ids.add(app_id)
        if session.get(Game, app_id):
            updated_games += 1
        else:
            new_games += 1

    return ImportPreviewResponse(
        filename=filename,
        total_rows=len(df),
        new_games=new_games,
        updated_games=updated_games,
        unchanged_games=0,
        duplicate_rows=len(app_ids) - len(unique_ids),
        duplicate_app_ids=duplicate_app_ids,
    )

def save_upload_to_temp(file: UploadFile) -> str:
    suffix = os.path.splitext(file.filename or "")[1] or ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        return temp_file.name

def load_uploaded_library(file: UploadFile) -> pd.DataFrame:
    temp_file_path = save_upload_to_temp(file)
    try:
        return load_steam_library(temp_file_path)
    finally:
        os.remove(temp_file_path)

@app.post("/upload/preview", response_model=ImportPreviewResponse)
async def preview_library_upload(file: UploadFile = File(...), session: Session = Depends(get_session)):
    try:
        df = load_uploaded_library(file)
        return preview_import(df, session, file.filename or "library.csv")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to preview file: {str(e)}")

@app.post("/upload")
async def upload_library(file: UploadFile = File(...), session: Session = Depends(get_session)):
    try:
        df = load_uploaded_library(file)
        preview = preview_import(df, session, file.filename or "library.csv")
        seen_app_ids = set()
        
        for _, row in df.iterrows():
            app_id = int(row['AppID'])
            if app_id in seen_app_ids:
                continue
            seen_app_ids.add(app_id)
            existing_game = session.get(Game, app_id)
            if existing_game:
                existing_game.name = str(row['Name'])
                existing_game.playtime_forever = int(row['Playtime_Forever'])
                # Only overwrite if we don't have valid data yet?
                # Actually, the user's CSV is the source of truth for playtime, but might be bad for tags.
                # If CSV has "Unknown" genre, keep existing DB genre if it's better.
                csv_genre = str(row.get('Genre', 'Unknown'))
                if csv_genre != 'Unknown' or existing_game.genre == 'Unknown':
                    existing_game.genre = csv_genre
                    
                csv_tags = str(row.get('Tags', 'Unknown'))
                if csv_tags != 'Unknown' or existing_game.tags == 'Unknown':
                    existing_game.tags = csv_tags
                
                apply_attention_heuristics(existing_game)
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
                apply_attention_heuristics(game)
                session.add(game)
        
        session.commit()
        sync_recommender_with_db()
        games_count = len(session.exec(select(Game)).all())
        return {
            "message": f"Successfully loaded library from {file.filename}",
            "games_count": games_count,
            "new_games": preview.new_games,
            "updated_games": preview.updated_games,
            "duplicate_rows": preview.duplicate_rows,
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")

def _clean_external_cell(value) -> Optional[str]:
    """Normalizes a pandas cell to a stripped string, or None if blank/NaN."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None

def _external_row_would_update(game: Game, genre: Optional[str], tags: Optional[str], playtime_minutes: Optional[float]) -> bool:
    """Whether the fill-only (non-replace) rule would actually change `game`."""
    if genre and (not game.genre or game.genre == "Unknown"):
        return True
    if tags and (not game.tags or game.tags == "Unknown"):
        return True
    if playtime_minutes is not None and not game.playtime_forever:
        return True
    return False

def _apply_external_metadata(game: Game, genre: Optional[str], tags: Optional[str], playtime_minutes: Optional[float], replace_metadata: bool) -> bool:
    """Fills (or, if replace_metadata, overwrites) genre/tags/playtime from an import row.
    Never touches status/attention/personal fields. Returns whether anything changed."""
    changed = False
    if genre and (replace_metadata or not game.genre or game.genre == "Unknown"):
        if game.genre != genre:
            game.genre = genre
            changed = True
    if tags and (replace_metadata or not game.tags or game.tags == "Unknown"):
        if game.tags != tags:
            game.tags = tags
            changed = True
    if playtime_minutes is not None and (replace_metadata or not game.playtime_forever):
        new_playtime = int(playtime_minutes)
        if game.playtime_forever != new_playtime:
            game.playtime_forever = new_playtime
            changed = True
    return changed

def classify_external_import_rows(df: pd.DataFrame, session: Session) -> List[dict]:
    """Validates and classifies each row of a normalized external-library import.

    Returns one entry per data row (1-based, matching the file), each with a
    `status` of invalid/duplicate/new/updated/skipped and the parsed fields
    needed to write it (or an `error` for invalid rows). See docs/import-format.md.
    """
    results = []
    seen_identities = set()

    for position, row in enumerate(df.to_dict("records"), start=1):
        title = _clean_external_cell(row.get("title"))
        platform = (_clean_external_cell(row.get("platform")) or "").lower()
        source = _clean_external_cell(row.get("source"))
        external_id = _clean_external_cell(row.get("external_id"))
        genre = _clean_external_cell(row.get("genre"))
        tags = _clean_external_cell(row.get("tags"))
        playtime_raw = _clean_external_cell(row.get("playtime_minutes"))

        error = None
        if not title:
            error = "title is required"
        elif platform == "steam":
            error = "platform 'steam' is not supported for import — Steam games sync automatically via Steam Sync"
        elif platform not in EXTERNAL_VALID_PLATFORMS:
            error = f"unsupported platform '{platform}'. Valid platforms: {', '.join(sorted(EXTERNAL_VALID_PLATFORMS))}"

        playtime_minutes = None
        if error is None and playtime_raw is not None:
            try:
                playtime_minutes = float(playtime_raw)
            except ValueError:
                error = f"playtime_minutes '{playtime_raw}' is not numeric"

        if error:
            results.append({"row": position, "status": "invalid", "error": f"Row {position}: {error}"})
            continue

        identity_key = ("source_id", source, external_id) if external_id else ("name_platform", title.lower(), platform)
        if identity_key in seen_identities:
            results.append({"row": position, "status": "duplicate", "error": None})
            continue
        seen_identities.add(identity_key)

        if external_id:
            matched_game = session.exec(
                select(Game).where(Game.source == source, Game.external_id == external_id)
            ).first()
        else:
            matched_game = session.exec(
                select(Game).where(col(Game.name).ilike(title), Game.platform == platform)
            ).first()

        entry = {
            "row": position,
            "error": None,
            "title": title,
            "platform": platform,
            "source": source,
            "external_id": external_id,
            "genre": genre,
            "tags": tags,
            "playtime_minutes": playtime_minutes,
            "matched_game": matched_game,
        }
        if matched_game:
            entry["status"] = "updated" if _external_row_would_update(matched_game, genre, tags, playtime_minutes) else "skipped"
        else:
            entry["status"] = "new"
        results.append(entry)

    return results

@app.post("/import/external/preview", response_model=ExternalImportPreviewResponse)
async def preview_external_import(file: UploadFile = File(...), session: Session = Depends(get_session)):
    temp_file_path = save_upload_to_temp(file)
    try:
        df = load_external_library(temp_file_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.remove(temp_file_path)

    rows = classify_external_import_rows(df, session)

    counts = {"new": 0, "updated": 0, "skipped": 0, "duplicates": 0}
    invalid = []
    for entry in rows:
        if entry["status"] == "invalid":
            invalid.append({"row": entry["row"], "error": entry["error"]})
        elif entry["status"] == "duplicate":
            counts["duplicates"] += 1
        else:
            counts[entry["status"]] += 1

    return ExternalImportPreviewResponse(
        filename=file.filename or "library.csv",
        total_rows=len(df),
        new=counts["new"],
        updated=counts["updated"],
        skipped=counts["skipped"],
        duplicates=counts["duplicates"],
        invalid=invalid,
    )

@app.post("/import/external", response_model=ExternalImportResponse)
async def import_external_library(
    file: UploadFile = File(...),
    replace_metadata: bool = Form(False),
    session: Session = Depends(get_session),
):
    temp_file_path = save_upload_to_temp(file)
    try:
        df = load_external_library(temp_file_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.remove(temp_file_path)

    rows = classify_external_import_rows(df, session)

    existing_ids = session.exec(select(Game.id).where(Game.id >= MANUAL_ID_FLOOR)).all()
    next_id = max(existing_ids, default=MANUAL_ID_FLOOR - 1) + 1

    imported = 0
    updated = 0
    skipped = 0
    duplicates = 0
    invalid = []

    for entry in rows:
        if entry["status"] == "invalid":
            invalid.append({"row": entry["row"], "error": entry["error"]})
            continue
        if entry["status"] == "duplicate":
            duplicates += 1
            continue
        if entry["status"] == "new":
            playtime_minutes = entry["playtime_minutes"]
            game = Game(
                id=next_id,
                name=entry["title"],
                platform=entry["platform"],
                source=entry["source"],
                external_id=entry["external_id"],
                genre=entry["genre"] or "Unknown",
                tags=entry["tags"] or "Unknown",
                playtime_forever=int(playtime_minutes) if playtime_minutes is not None else 0,
                status=GameStatus.LIBRARY,
                attention_level=AttentionLevel.UNSET,
                # ponytail: no SteamGridDB art lookup here — a batch import would hammer
                # the API; header images stay unset until the enrich flow picks them up.
            )
            next_id += 1
            session.add(game)
            imported += 1
        else:
            game = entry["matched_game"]
            changed = _apply_external_metadata(game, entry["genre"], entry["tags"], entry["playtime_minutes"], replace_metadata)
            if changed:
                session.add(game)
                updated += 1
            else:
                skipped += 1

    session.commit()
    sync_recommender_with_db()

    return ExternalImportResponse(
        imported=imported,
        updated=updated,
        skipped=skipped,
        duplicates=duplicates,
        invalid=invalid,
    )

async def run_steam_sync(session: Session) -> dict:
    api_key = os.getenv("STEAM_API_KEY")
    steam_id = os.getenv("STEAM_ID")

    games = await fetch_owned_games(api_key, steam_id)
    if games is None:
        raise HTTPException(status_code=502, detail="Steam API returned no data. Check your Steam ID and that your profile's game details are public.")

    added = 0
    updated = 0

    for g in games:
        appid = g.get("appid")
        if not appid:
            continue
        existing = session.get(Game, appid)
        if existing:
            # Steam omits/blanks names for some delisted apps; keep the old one
            existing.name = g.get("name") or existing.name
            old_playtime = existing.playtime_forever
            new_playtime = g.get("playtime_forever", 0)
            existing.playtime_forever = new_playtime
            # Only increases count as play sessions; decreases (stat resets) are anomalies
            if new_playtime > old_playtime:
                session.add(PlayEvent(game_id=existing.id, event_type="playtime", old_value=str(old_playtime), new_value=str(new_playtime)))
            session.add(existing)
            updated += 1
        else:
            game = Game(
                id=appid,
                name=g.get("name") or f"App {appid}",
                playtime_forever=g.get("playtime_forever", 0),
                genre="Unknown",
                tags="Unknown",
                status=GameStatus.LIBRARY,
                attention_level=AttentionLevel.UNSET,
                platform="steam"
            )
            apply_attention_heuristics(game)
            session.add(game)
            added += 1

    session.commit()
    sync_recommender_with_db()
    result = {
        "added": added,
        "updated": updated,
        "total": len(games),
        "message": f"Steam sync complete: {added} added, {updated} updated.",
    }
    session.add(SyncRun(success=True, message=result["message"]))
    session.commit()
    return result

def steam_sync_interval_seconds() -> Optional[int]:
    """None = auto-sync disabled (no creds or SYNC_INTERVAL_HOURS=0)."""
    if not (os.getenv("STEAM_API_KEY") and os.getenv("STEAM_ID")):
        return None
    try:
        hours = float(os.getenv("SYNC_INTERVAL_HOURS", "24"))
    except ValueError:
        return None
    if hours <= 0:
        return None
    return int(hours * 3600)

async def run_scheduled_enrichment(limit: int = 50):
    with Session(engine) as session:
        existing = session.exec(
            select(EnrichmentJob).where(EnrichmentJob.status == "running")
        ).first()
        if existing:
            print("Auto-enrich skipped: enrichment already in progress.")
            return
        total = len(session.exec(enrichment_candidates_query(limit)).all())
        if total == 0:
            return
        job = EnrichmentJob(total=total)
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id
    await process_enrichment(job_id, limit)

async def steam_sync_scheduler():
    while True:
        try:
            with Session(engine) as session:
                result = await run_steam_sync(session)
                print(f"Auto-sync: {result['message']}")
        except Exception as e:
            print(f"Auto-sync failed: {e}")
            try:
                with Session(engine) as fail_session:
                    fail_session.add(SyncRun(success=False, message=str(e)))
                    fail_session.commit()
            except Exception as record_error:
                print(f"Auto-sync failure recording failed: {record_error}")
        try:
            await run_scheduled_enrichment()
        except Exception as e:
            print(f"Auto-enrich failed: {e}")
        interval = steam_sync_interval_seconds()
        if interval is None:
            break
        await asyncio.sleep(interval)

@app.post("/sync/steam")
async def sync_steam_library(session: Session = Depends(get_session)):
    api_key = os.getenv("STEAM_API_KEY")
    steam_id = os.getenv("STEAM_ID")
    if not api_key or not steam_id:
        raise HTTPException(status_code=503, detail="Steam sync not configured. Set STEAM_API_KEY and STEAM_ID environment variables.")

    return await run_steam_sync(session)

@app.post("/recommendations/decisions", response_model=RecommendationDecision)
async def create_recommendation_decision(
    payload: RecommendationDecisionCreate,
    session: Session = Depends(get_session),
):
    game = session.get(Game, payload.game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    decision = RecommendationDecision(
        game_id=payload.game_id,
        decision=payload.decision,
        reason=payload.reason,
        mood=payload.mood,
        tags_snapshot=game.tags,
    )
    session.add(decision)
    session.commit()
    session.refresh(decision)
    sync_recommender_with_db()
    return decision

@app.get("/recommendations/decisions", response_model=List[RecommendationDecision])
async def list_recommendation_decisions(session: Session = Depends(get_session)):
    return session.exec(
        select(RecommendationDecision).order_by(
            RecommendationDecision.created_at.desc(), RecommendationDecision.id.desc()
        )
    ).all()

@app.delete("/recommendations/decisions")
async def clear_recommendation_decisions(session: Session = Depends(get_session)):
    decisions = session.exec(select(RecommendationDecision)).all()
    count = len(decisions)
    for decision in decisions:
        session.delete(decision)
    session.commit()
    sync_recommender_with_db()
    return {"cleared": count}

CONTINUATION_STATUS_PRIORITY = {
    GameStatus.PLAYING: 0,
    GameStatus.UP_NEXT: 1,
    GameStatus.PAUSED: 2,
}

# Same burst-friendly tag family the "short_session" mood uses in the recommender.
SHORT_SESSION_TAG_PATTERN = re.compile(
    r"Roguelike|Roguelite|Arcade|Puzzle|Casual|Platformer|Card Game", re.IGNORECASE
)

# NOTE: this must stay above the plain GET /recommend route below — a literal
# "/recommend/continuation" path segment would otherwise be ambiguous if /recommend
# ever grows a path parameter. There is no ambiguity today, but declaring it first
# keeps that invariant cheap to preserve.
@app.get("/recommend/continuation")
async def recommend_continuation(session: Session = Depends(get_session)):
    candidates = session.exec(
        select(Game).where(
            col(Game.status).in_([GameStatus.PLAYING, GameStatus.UP_NEXT, GameStatus.PAUSED])
        )
    ).all()

    if not candidates:
        return {"short": [], "session": [], "finish": []}

    game_ids = [game.id for game in candidates]
    events = session.exec(
        select(PlayEvent)
        .where(col(PlayEvent.game_id).in_(game_ids))
        .order_by(PlayEvent.created_at.desc())
    ).all()
    last_activity = {}
    for event in events:
        last_activity.setdefault(event.game_id, event.created_at)

    now = utc_now()
    items = []
    for game in candidates:
        estimate = estimate_remaining(game)
        reasons = []

        if game.status == GameStatus.PLAYING:
            reasons.append("You're playing this now")
        elif game.status == GameStatus.UP_NEXT:
            reasons.append("Next in your queue")
        elif game.status == GameStatus.PAUSED:
            reasons.append(f"Paused — {game.return_when}" if game.return_when else "Paused")

        last_active = last_activity.get(game.id)
        if last_active is not None:
            last_active_aware = last_active if last_active.tzinfo else last_active.replace(tzinfo=timezone.utc)
            if now - last_active_aware < timedelta(days=7):
                reasons.append("Active in the last 7 days")

        if estimate is not None:
            reasons.append(estimate["label"])

        items.append({"game": game, "estimate": estimate, "reasons": reasons})

    def rank_key(item):
        game = item["game"]
        estimate = item["estimate"]
        minutes_key = (1, 0) if estimate is None else (0, estimate["minutes"])
        return (CONTINUATION_STATUS_PRIORITY[game.status], minutes_key, game.name.lower())

    ranked = sorted(items, key=rank_key)

    def build_bucket(predicate, cap: int = 3, fallback: bool = False):
        bucket = [item for item in ranked if predicate(item)]
        if fallback and len(bucket) < cap:
            chosen_ids = {item["game"].id for item in bucket}
            for item in ranked:
                if len(bucket) >= cap:
                    break
                if item["game"].id in chosen_ids:
                    continue
                bucket.append(item)
                chosen_ids.add(item["game"].id)
            bucket.sort(key=rank_key)
        return bucket[:cap]

    def is_short_candidate(item) -> bool:
        game = item["game"]
        estimate = item["estimate"]
        if game.session_tags and "burst_friendly" in game.session_tags:
            return True
        if game.tags and SHORT_SESSION_TAG_PATTERN.search(game.tags):
            return True
        if estimate is not None and estimate["minutes"] <= 60:
            return True
        return False

    def is_session_candidate(item) -> bool:
        estimate = item["estimate"]
        return estimate is not None and 60 < estimate["minutes"] <= 240

    def is_finish_candidate(item) -> bool:
        estimate = item["estimate"]
        if estimate is None:
            return False
        if estimate["confidence"] == "beyond_typical":
            return True
        return estimate["confidence"] == "rough_estimate" and estimate["minutes"] <= 720

    def serialize(item):
        result = item["game"].model_dump()
        result["remaining_estimate"] = item["estimate"]
        result["reasons"] = item["reasons"]
        return result

    return {
        "short": [serialize(item) for item in build_bucket(is_short_candidate)],
        "session": [serialize(item) for item in build_bucket(is_session_candidate, fallback=True)],
        "finish": [serialize(item) for item in build_bucket(is_finish_candidate)],
    }

# Deliberately different ordering from CONTINUATION_STATUS_PRIORITY: resume is
# progress-first (actively playing beats paused beats queued).
RESUME_STATUS_PRIORITY = {
    GameStatus.PLAYING: 0,
    GameStatus.PAUSED: 1,
    GameStatus.UP_NEXT: 2,
}

# See NOTE above /recommend/continuation — same invariant applies here.
@app.get("/recommend/resume")
async def recommend_resume(session: Session = Depends(get_session)):
    candidates = session.exec(
        select(Game).where(
            col(Game.status).in_([GameStatus.PLAYING, GameStatus.PAUSED, GameStatus.UP_NEXT])
        )
    ).all()

    if not candidates:
        return {"candidate": None}

    game_ids = [game.id for game in candidates]
    events = session.exec(
        select(PlayEvent)
        .where(col(PlayEvent.game_id).in_(game_ids))
        .order_by(PlayEvent.created_at.desc())
    ).all()
    last_activity = {}
    for event in events:
        last_activity.setdefault(event.game_id, event.created_at)

    now = utc_now()
    items = []
    for game in candidates:
        estimate = estimate_remaining(game)
        reasons = []

        if game.status == GameStatus.PLAYING:
            reasons.append("You're playing this now")
        elif game.status == GameStatus.PAUSED:
            reasons.append(f"Paused — {game.return_when}" if game.return_when else "Paused")
        elif game.status == GameStatus.UP_NEXT:
            reasons.append("Next in your queue")

        if game.current_note:
            reasons.append(f"Your note: {game.current_note}")

        last_active = last_activity.get(game.id)
        recent = False
        if last_active is not None:
            last_active_aware = last_active if last_active.tzinfo else last_active.replace(tzinfo=timezone.utc)
            recent = now - last_active_aware < timedelta(days=14)
            if recent:
                reasons.append("Active in the last 14 days")

        if estimate is not None:
            reasons.append(estimate["label"])

        items.append({
            "game": game,
            "estimate": estimate,
            "reasons": reasons,
            "recent": recent,
            "last_active": last_active,
        })

    def rank_key(item):
        game = item["game"]
        estimate = item["estimate"]
        recency_key = 0 if item["recent"] else 1
        notes_key = 0 if (game.return_when or game.current_note) else 1
        queue_key = game.queue_position if game.queue_position is not None else 10**9
        minutes_key = (1, 0) if estimate is None else (0, estimate["minutes"])
        return (
            RESUME_STATUS_PRIORITY[game.status],
            recency_key,
            notes_key,
            queue_key,
            minutes_key,
            game.name.lower(),
        )

    ranked = sorted(items, key=rank_key)
    top = ranked[0]
    game = top["game"]

    result = game.model_dump()
    result["remaining_estimate"] = top["estimate"]
    result["reasons"] = top["reasons"]
    last_active = top["last_active"]
    result["last_activity_at"] = last_active.isoformat() if last_active is not None else None
    result["launch_url"] = f"steam://rungameid/{game.id}" if game.platform == "steam" else None

    return {"candidate": result}

@app.get("/recommend", response_model=RecommendationResponse)
async def recommend_game(
    genre: Optional[str] = None,
    tag: Optional[str] = None,
    unplayed_only: bool = False,
    length: Optional[str] = Query(None, pattern="^(short|medium|long)$"),
    attention_level: Optional[str] = Query(None, pattern="^(casual|focused)$"),
    mood: Optional[str] = Query(None, pattern="^(zone_out|story_night|short_session|finish_something|surprise_me)$"),
    available_minutes: Optional[int] = Query(None, ge=5, le=600),
    energy: Optional[str] = Query(None, pattern="^(low|medium|high)$"),
    context: Optional[str] = Query(None, pattern="^(desk|couch|handheld|podcast)$"),
    count: int = Query(1, ge=1, le=5)
):
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

    games = recommender.recommend_many(
        count,
        genre=genre,
        tag=tag,
        unplayed_only=unplayed_only,
        min_length=min_len,
        max_length=max_len,
        attention_level=attention_level,
        mood=mood,
        available_minutes=available_minutes,
        energy=energy,
        context=context,
    )

    if not games:
        raise HTTPException(status_code=404, detail="No suitable game found matching your criteria.")

    def serialize(game):
        result = game.to_dict()
        result["score"] = int(result.get("score", 0))
        result["reasons"] = list(result.get("reasons") or [])
        return result

    result = serialize(games[0])
    result["alternates"] = [serialize(game) for game in games[1:]]
    return result

if __name__ == "__main__":
    print("Starting Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
