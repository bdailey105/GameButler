from src.models import Game, AttentionLevel

# Heuristic mappings for attention levels
CASUAL_TAGS = {
    "arcade", "casual", "puzzle", "clicker", "idler", "card game", 
    "bullet hell", "roguelike action", "survivor-like", "match 3",
    "hidden object", "tower defense", "physics"
}

FOCUSED_TAGS = {
    "story rich", "rpg", "strategy", "visual novel", "simulation", 
    "horror", "detective", "immersive sim", "cinematic", "rpg", 
    "open world", "narrative", "deep lore"
}

def apply_attention_heuristics(game: Game) -> Game:
    """
    Applies heuristics to guess attention level if currently unset.
    Manual overrides are respected.
    """
    if game.attention_level != AttentionLevel.UNSET:
        return game
    
    # Normalize tags for comparison
    tags = [t.strip().lower() for t in (game.tags or "").split(";")]
    genres = [g.strip().lower() for g in (game.genre or "").split(";")]
    all_metadata = set(tags + genres)
    
    # Check for focused tags first (err on the side of higher attention)
    if any(tag in all_metadata for tag in FOCUSED_TAGS):
        game.attention_level = AttentionLevel.FOCUSED
    elif any(tag in all_metadata for tag in CASUAL_TAGS):
        game.attention_level = AttentionLevel.CASUAL
        
    return game
