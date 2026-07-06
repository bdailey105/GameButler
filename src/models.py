from typing import Optional
from enum import Enum
from datetime import UTC, datetime
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
    queue_position: Optional[int] = None

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None
