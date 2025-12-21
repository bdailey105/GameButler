from src.models import Game, AttentionLevel
from src.logic import apply_attention_heuristics

def test_apply_attention_heuristics_casual():
    game = Game(id=1, name="Casual Game", tags="Arcade; Puzzle", attention_level=AttentionLevel.UNSET)
    apply_attention_heuristics(game)
    assert game.attention_level == AttentionLevel.CASUAL

def test_apply_attention_heuristics_focused():
    game = Game(id=2, name="Focused Game", tags="Story Rich; RPG", attention_level=AttentionLevel.UNSET)
    apply_attention_heuristics(game)
    assert game.attention_level == AttentionLevel.FOCUSED

def test_apply_attention_heuristics_override_respected():
    # If already set, should not change
    game = Game(id=3, name="Manual Game", tags="Arcade", attention_level=AttentionLevel.FOCUSED)
    apply_attention_heuristics(game)
    assert game.attention_level == AttentionLevel.FOCUSED

def test_apply_attention_heuristics_conflict_prefers_focused():
    # If both tags are present, we prefer focused for safety
    game = Game(id=4, name="Complex Game", tags="Arcade; Story Rich", attention_level=AttentionLevel.UNSET)
    apply_attention_heuristics(game)
    assert game.attention_level == AttentionLevel.FOCUSED
