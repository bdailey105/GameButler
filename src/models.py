from typing import Optional
from enum import Enum
from datetime import date, datetime, timezone
from sqlmodel import SQLModel, Field
from pydantic import field_validator

SESSION_TAGS = {"burst_friendly", "controller_only", "podcast_friendly"}

def _validate_session_tags(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value
    entries = [entry.strip() for entry in value.split(";")]
    invalid = [entry for entry in entries if entry not in SESSION_TAGS]
    if invalid:
        raise ValueError(
            f"Invalid session_tags entry: {invalid[0]!r}. Must be one of {sorted(SESSION_TAGS)}"
        )
    return value

class GameStatus(str, Enum):
    LIBRARY = "library"
    UP_NEXT = "up_next"
    PLAYING = "playing"
    PAUSED = "paused"
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
    source: Optional[str] = None  # external library source, e.g. "nintendo_export"
    external_id: Optional[str] = None  # id within that source
    queue_position: Optional[int] = None
    average_playtime: Optional[int] = None  # minutes to beat (main story), None = not yet looked up, 0 = HLTB has no data
    enrich_attempts: int = Field(default=0)
    personal_rating: Optional[int] = None  # 1-5; None = unrated
    started_on: Optional[date] = None
    completed_on: Optional[date] = None
    current_note: Optional[str] = None  # concise "where I left off"
    session_tags: Optional[str] = None  # semicolon list: burst_friendly;controller_only;podcast_friendly
    return_when: Optional[str] = None  # optional "return when..." note for paused games

    @field_validator("session_tags")
    @classmethod
    def _check_session_tags(cls, value: Optional[str]) -> Optional[str]:
        return _validate_session_tags(value)

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
    session_tags: Optional[str] = None
    return_when: Optional[str] = None

    @field_validator("session_tags")
    @classmethod
    def _check_session_tags(cls, value: Optional[str]) -> Optional[str]:
        return _validate_session_tags(value)

class QueueReorder(SQLModel):
    app_ids: list[int]

class BulkGameUpdate(SQLModel):
    app_ids: list[int]
    status: Optional[GameStatus] = None
    attention_level: Optional[AttentionLevel] = None
    session_tags: Optional[str] = None

    @field_validator("session_tags")
    @classmethod
    def _check_session_tags(cls, value: Optional[str]) -> Optional[str]:
        return _validate_session_tags(value)

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

class RecommendationDecision(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(foreign_key="game.id", index=True)
    decision: str  # accepted_play | accepted_queue | rejected | deferred | more_like_this | less_like_this
    reason: Optional[str] = None  # not_in_the_mood | too_long | too_demanding | bounced_off | defer_for_now
    mood: Optional[str] = None  # recommendation context at decision time
    tags_snapshot: Optional[str] = None  # game's tags when decided — keeps affinity deterministic
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Allowed values for SessionOutcome.fit — "skipped" is a real, persisted answer
# (the user declined to reflect), distinct from there being no outcome at all.
SESSION_OUTCOME_FITS = {"great_fit", "partly", "not_a_fit", "skipped"}

class SessionOutcome(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    decision_id: int = Field(foreign_key="recommendationdecision.id", unique=True, index=True)
    game_id: int = Field(foreign_key="game.id", index=True)
    fit: str  # great_fit | partly | not_a_fit | skipped
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SessionOutcomeCreate(SQLModel):
    decision_id: int
    fit: str

    @field_validator("fit")
    @classmethod
    def _check_fit(cls, value: str) -> str:
        if value not in SESSION_OUTCOME_FITS:
            raise ValueError(f"Invalid fit: {value!r}. Must be one of {sorted(SESSION_OUTCOME_FITS)}")
        return value

# Allowed values for ArchaeologyDismissal.action — "dismissed" is forever, "deferred"
# hides the dig for a rolling window (see /archaeology neglect-window logic in api.py).
ARCHAEOLOGY_DISMISSAL_ACTIONS = {"dismissed", "deferred"}

class ArchaeologyDismissal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(foreign_key="game.id", unique=True, index=True)
    action: str  # dismissed | deferred
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ArchaeologyDismissalCreate(SQLModel):
    action: str

    @field_validator("action")
    @classmethod
    def _check_action(cls, value: str) -> str:
        if value not in ARCHAEOLOGY_DISMISSAL_ACTIONS:
            raise ValueError(f"Invalid action: {value!r}. Must be one of {sorted(ARCHAEOLOGY_DISMISSAL_ACTIONS)}")
        return value

# Allowed values mirror the /recommend query params exactly — profiles are
# explicit presets of those same parameters, not a separate vocabulary.
CONTEXT_PROFILE_LENGTHS = {"short", "medium", "long"}
CONTEXT_PROFILE_ATTENTION_LEVELS = {"casual", "focused"}
CONTEXT_PROFILE_MOODS = {"zone_out", "story_night", "short_session", "finish_something", "surprise_me"}
CONTEXT_PROFILE_ENERGY_LEVELS = {"low", "medium", "high"}
CONTEXT_PROFILE_CONTEXTS = {"desk", "couch", "handheld", "podcast"}

def _validate_choice(value: Optional[str], allowed: set, label: str) -> Optional[str]:
    if value is None:
        return value
    if value not in allowed:
        raise ValueError(f"Invalid {label}: {value!r}. Must be one of {sorted(allowed)}")
    return value

def _check_profile_length(value: Optional[str]) -> Optional[str]:
    return _validate_choice(value, CONTEXT_PROFILE_LENGTHS, "length")

def _check_profile_attention_level(value: Optional[str]) -> Optional[str]:
    return _validate_choice(value, CONTEXT_PROFILE_ATTENTION_LEVELS, "attention_level")

def _check_profile_mood(value: Optional[str]) -> Optional[str]:
    return _validate_choice(value, CONTEXT_PROFILE_MOODS, "mood")

def _check_profile_energy(value: Optional[str]) -> Optional[str]:
    return _validate_choice(value, CONTEXT_PROFILE_ENERGY_LEVELS, "energy")

def _check_profile_context(value: Optional[str]) -> Optional[str]:
    return _validate_choice(value, CONTEXT_PROFILE_CONTEXTS, "context")

class ContextProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    mood: Optional[str] = None
    energy: Optional[str] = None
    context: Optional[str] = None
    attention_level: Optional[str] = None
    length: Optional[str] = None
    genre: Optional[str] = None
    tag: Optional[str] = None
    available_minutes: Optional[int] = Field(default=None, ge=5, le=600)
    unplayed_only: bool = False

    @field_validator("length")
    @classmethod
    def _validate_length(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_length(value)

    @field_validator("attention_level")
    @classmethod
    def _validate_attention_level(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_attention_level(value)

    @field_validator("mood")
    @classmethod
    def _validate_mood(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_mood(value)

    @field_validator("energy")
    @classmethod
    def _validate_energy(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_energy(value)

    @field_validator("context")
    @classmethod
    def _validate_context(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_context(value)

class ContextProfileCreate(SQLModel):
    name: str
    mood: Optional[str] = None
    energy: Optional[str] = None
    context: Optional[str] = None
    attention_level: Optional[str] = None
    length: Optional[str] = None
    genre: Optional[str] = None
    tag: Optional[str] = None
    available_minutes: Optional[int] = Field(default=None, ge=5, le=600)
    unplayed_only: bool = False

    @field_validator("length")
    @classmethod
    def _validate_length(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_length(value)

    @field_validator("attention_level")
    @classmethod
    def _validate_attention_level(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_attention_level(value)

    @field_validator("mood")
    @classmethod
    def _validate_mood(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_mood(value)

    @field_validator("energy")
    @classmethod
    def _validate_energy(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_energy(value)

    @field_validator("context")
    @classmethod
    def _validate_context(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_context(value)

class Rotation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RotationGame(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    rotation_id: int = Field(foreign_key="rotation.id", index=True)
    game_id: int = Field(foreign_key="game.id", index=True)

class RotationCreate(SQLModel):
    name: str

class RotationUpdate(SQLModel):
    name: Optional[str] = None
    active: Optional[bool] = None

class RotationGameAdd(SQLModel):
    game_id: int

class ContextProfileUpdate(SQLModel):
    name: Optional[str] = None
    mood: Optional[str] = None
    energy: Optional[str] = None
    context: Optional[str] = None
    attention_level: Optional[str] = None
    length: Optional[str] = None
    genre: Optional[str] = None
    tag: Optional[str] = None
    available_minutes: Optional[int] = Field(default=None, ge=5, le=600)
    unplayed_only: Optional[bool] = None

    @field_validator("length")
    @classmethod
    def _validate_length(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_length(value)

    @field_validator("attention_level")
    @classmethod
    def _validate_attention_level(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_attention_level(value)

    @field_validator("mood")
    @classmethod
    def _validate_mood(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_mood(value)

    @field_validator("energy")
    @classmethod
    def _validate_energy(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_energy(value)

    @field_validator("context")
    @classmethod
    def _validate_context(cls, value: Optional[str]) -> Optional[str]:
        return _check_profile_context(value)
