import re

from src.models import Game, AttentionLevel

def normalize(value: str) -> str:
    """Lowercase and strip everything except a-z0-9, so "Story Rich",
    "story-rich", and "story rich" all collapse to the same token."""
    return re.sub(r"[^a-z0-9]", "", value.lower())

# Heuristic mappings for attention levels (raw strings; normalized at match time)
CASUAL_TAGS = {
    "arcade", "casual", "puzzle", "clicker", "idler", "card game",
    "bullet hell", "roguelike action", "survivor-like", "match 3",
    "hidden object", "tower defense", "physics",
    "relaxing", "cozy", "idle", "incremental", "auto battler",
    "shoot em up", "twin stick shooter", "rhythm", "party game",
    "fishing", "roguelite", "vampire survivors-like", "runner",
    "trivia", "word game", "solitaire",
}

FOCUSED_TAGS = {
    "story rich", "rpg", "strategy", "visual novel", "simulation",
    "horror", "detective", "immersive sim", "cinematic",
    "open world", "narrative", "deep lore",
    "jrpg", "crpg", "grand strategy", "4x", "tactics", "tactical",
    "souls-like", "metroidvania", "survival horror", "mystery",
    "choices matter", "walking simulator", "point and click",
}

CASUAL_TAGS_NORM = {normalize(tag) for tag in CASUAL_TAGS}
FOCUSED_TAGS_NORM = {normalize(tag) for tag in FOCUSED_TAGS}

def _keyword_matches_token(keyword: str, token: str) -> bool:
    """Both already normalized. Substring match either direction, but guard
    against junk hits from very short strings (e.g. "4x") by requiring an
    exact match unless both sides are at least 3 characters."""
    if len(keyword) >= 3 and len(token) >= 3:
        return keyword in token or token in keyword
    return keyword == token

def _any_keyword_matches(keywords_norm: set, tokens_norm: set) -> bool:
    return any(
        _keyword_matches_token(keyword, token)
        for keyword in keywords_norm
        for token in tokens_norm
    )

def apply_attention_heuristics(game: Game) -> Game:
    """
    Applies heuristics to guess attention level if currently unset.
    Manual overrides are respected.
    """
    if game.attention_level != AttentionLevel.UNSET:
        return game

    tags = [t.strip() for t in (game.tags or "").split(";")]
    genres = [g.strip() for g in (game.genre or "").split(";")]
    tokens_norm = {normalize(token) for token in tags + genres if token}
    tokens_norm.discard("")

    # Check for focused tags first (err on the side of higher attention)
    if _any_keyword_matches(FOCUSED_TAGS_NORM, tokens_norm):
        game.attention_level = AttentionLevel.FOCUSED
        game.attention_source = "auto"
    elif _any_keyword_matches(CASUAL_TAGS_NORM, tokens_norm):
        game.attention_level = AttentionLevel.CASUAL
        game.attention_source = "auto"

    return game
