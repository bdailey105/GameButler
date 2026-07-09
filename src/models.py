from typing import Optional
from enum import Enum
from datetime import date, datetime, timezone
from sqlmodel import SQLModel, Field

class GameStatus(str, Enum):
    LIBRARY = "library"
    UP_NEXT = "up_next"
    PLAYING = "playing"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

class AttentionLevel(str, Enum):
    UNSET = "unset"
    CASUAL = "casual"
    FOCUSED = "focused"

class GameBase(SQLModel):
    name: str
    playtime_forever: int
    genre: Optional[str] = None
    tags: Optional[str] = None
    header_image: Optional[str] = None
    short_description: Optional[str] = None
    status: GameStatus = Field(default=GameStatus.LIBRARY)
    attention_level: AttentionLevel = Field(default=AttentionLevel.UNSET)
    attention_source: Optional[str] = None  # "manual" | "auto" | None (never tagged)
    platform: str = Field(default="steam")
    queue_position: Optional[int] = None
    average_playtime: Optional[int] = None  # minutes to beat (main story), None = not yet looked up, 0 = HLTB has no data
    enrich_attempts: int = Field(default=0)
    personal_rating: Optional[int] = None  # 1-5; None = unrated
    started_on: Optional[date] = None
    completed_on: Optional[date] = None
    current_note: Optional[str] = None  # concise "where I left off"

class Game(GameBase, table=True):
    id: int = Field(default=None, primary_key=True)

class GameCreate(GameBase):
    id: int # Steam AppID

class GameUpdate(SQLModel):
    name: Optional[str] = None
    playtime_forever: Optional[int] = None
    genre: Optional[str] = None
    tags: Optional[str] = None
    header_image: Optional[str] = None
    short_description: Optional[str] = None
    status: Optional[GameStatus] = None
    attention_level: Optional[AttentionLevel] = None
    queue_position: Optional[int] = None
    personal_rating: Optional[int] = Field(default=None, ge=1, le=5)
    started_on: Optional[date] = None
    completed_on: Optional[date] = None
    current_note: Optional[str] = None

class QueueReorder(SQLModel):
    app_ids: list[int]

class EnrichmentJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = "running"
    total: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    error_summary: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

class SyncRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    finished_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    message: str = ""

class PlayEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(foreign_key="game.id", index=True)
    event_type: str  # "status" or "playtime"
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class JournalEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(foreign_key="game.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    text: str
