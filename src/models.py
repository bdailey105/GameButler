from typing import Optional
from enum import Enum
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
    status: GameStatus = Field(default=GameStatus.LIBRARY)
    attention_level: AttentionLevel = Field(default=AttentionLevel.UNSET)

class Game(GameBase, table=True):
    id: int = Field(default=None, primary_key=True)

class GameCreate(GameBase):
    id: int # Steam AppID

class GameUpdate(SQLModel):
    name: Optional[str] = None
    playtime_forever: Optional[int] = None
    genre: Optional[str] = None
    tags: Optional[str] = None
    status: Optional[GameStatus] = None
    attention_level: Optional[AttentionLevel] = None
