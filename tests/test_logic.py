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

def test_apply_attention_heuristics_substring_match_genre():
    # "rpg" keyword should hit inside a compound genre token like "Action RPG"
    game = Game(id=5, name="Substring Genre Game", genre="Action RPG", attention_level=AttentionLevel.UNSET)
    apply_attention_heuristics(game)
    assert game.attention_level == AttentionLevel.FOCUSED

def test_apply_attention_heuristics_substring_match_tag():
    game = Game(id=6, name="Substring Tag Game", tags="Roguelite", attention_level=AttentionLevel.UNSET)
    apply_attention_heuristics(game)
    assert game.attention_level == AttentionLevel.CASUAL

def test_apply_attention_heuristics_normalizes_punctuation_variants():
    # "Story-Rich" should normalize the same as "Story Rich"
    game = Game(id=7, name="Normalized Game", tags="Story-Rich", attention_level=AttentionLevel.UNSET)
    apply_attention_heuristics(game)
    assert game.attention_level == AttentionLevel.FOCUSED

def test_apply_attention_heuristics_manual_override_still_respected():
    game = Game(id=8, name="Manual Override Game", tags="Roguelite", attention_level=AttentionLevel.CASUAL)
    apply_attention_heuristics(game)
    assert game.attention_level == AttentionLevel.CASUAL

def test_apply_attention_heuristics_sets_source_auto():
    game = Game(id=9, name="Auto Sourced Game", tags="Arcade", attention_level=AttentionLevel.UNSET)
    apply_attention_heuristics(game)
    assert game.attention_level == AttentionLevel.CASUAL
    assert game.attention_source == "auto"
