import pytest
import pandas as pd
from src.recommender import GameRecommender
from src.models import GameStatus, AttentionLevel

@pytest.fixture
def sample_df():
    data = {
        'AppID': [1, 2, 3, 4, 5],
        'Name': ['Short Game', 'Long Game', 'Medium Game', 'Zero Length', 'Just Right'],
        'Playtime_Forever': [100, 50, 0, 20, 30],
        'Average_Playtime': [60, 3000, 600, 0, 1200], # Minutes: 1h, 50h, 10h, 0h, 20h
        'Genre': ['Action', 'RPG', 'Action', 'Puzzle', 'Action'],
        'Tags': ['Indie', 'Story', 'Shooter', 'Logic', 'FPS']
    }
    return pd.DataFrame(data)

def test_recommend_random(sample_df):
    recommender = GameRecommender(sample_df)
    game = recommender.recommend_random()
    assert game is not None

def test_recommend_by_length_short(sample_df):
    recommender = GameRecommender(sample_df)
    # Filter for games <= 1 hour (60 mins)
    game = recommender.recommend(max_length=60)
    assert game is not None
    assert game['Average_Playtime'] <= 60
    # Should likely match 'Short Game' or 'Zero Length'
    assert game['Name'] in ['Short Game', 'Zero Length']

def test_recommend_by_length_long(sample_df):
    recommender = GameRecommender(sample_df)
    # Filter for games >= 40 hours (2400 mins)
    game = recommender.recommend(min_length=2400)
    assert game is not None
    assert game['Average_Playtime'] >= 2400
    assert game['Name'] == 'Long Game'

def test_recommend_by_length_range(sample_df):
    recommender = GameRecommender(sample_df)
    # Between 5 and 15 hours (300 - 900 mins)
    game = recommender.recommend(min_length=300, max_length=900)
    assert game is not None
    assert 300 <= game['Average_Playtime'] <= 900
    assert game['Name'] == 'Medium Game'

def test_recommend_excludes_completed_and_abandoned_by_default(sample_df):
    sample_df['status'] = [
        GameStatus.COMPLETED,
        GameStatus.ABANDONED,
        GameStatus.COMPLETED,
        GameStatus.ABANDONED,
        GameStatus.LIBRARY,
    ]
    recommender = GameRecommender(sample_df)

    game = recommender.recommend()

    assert game is not None
    assert game['Name'] == 'Just Right'

def test_recommend_excludes_completed_and_abandoned_string_values(sample_df):
    sample_df['status'] = [
        GameStatus.COMPLETED.value,
        GameStatus.ABANDONED.value,
        GameStatus.COMPLETED.value,
        GameStatus.ABANDONED.value,
        GameStatus.LIBRARY.value,
    ]
    recommender = GameRecommender(sample_df)

    game = recommender.recommend()

    assert game is not None
    assert game['Name'] == 'Just Right'

def test_recommend_is_deterministic_and_prefers_up_next(sample_df):
    sample_df['status'] = [
        GameStatus.LIBRARY,
        GameStatus.UP_NEXT,
        GameStatus.LIBRARY,
        GameStatus.LIBRARY,
        GameStatus.LIBRARY,
    ]
    recommender = GameRecommender(sample_df)

    first = recommender.recommend()
    second = recommender.recommend()

    assert first['Name'] == 'Long Game'
    assert second['Name'] == 'Long Game'
    assert first['score'] == 38
    assert 'Already in your Up Next queue' in first['reasons']

def test_attention_and_unplayed_influence_score(sample_df):
    sample_df['status'] = [GameStatus.LIBRARY] * len(sample_df)
    sample_df['attention_level'] = [
        AttentionLevel.CASUAL,
        AttentionLevel.FOCUSED,
        AttentionLevel.CASUAL,
        AttentionLevel.FOCUSED,
        AttentionLevel.CASUAL,
    ]
    recommender = GameRecommender(sample_df)

    game = recommender.recommend(attention_level='casual', unplayed_only=True)

    assert game['Name'] == 'Medium Game'
    assert game['score'] == 40
    assert 'Matches your casual attention setting' in game['reasons']
    assert 'You asked for something unplayed' in game['reasons']

def test_length_constraints_add_reason(sample_df):
    recommender = GameRecommender(sample_df)

    game = recommender.recommend(min_length=300, max_length=900)

    assert game['Name'] == 'Medium Game'
    assert 'Fits your session length' in game['reasons']

def test_zone_out_mood_prefers_casual_games(sample_df):
    sample_df['attention_level'] = [
        AttentionLevel.CASUAL,
        AttentionLevel.FOCUSED,
        AttentionLevel.FOCUSED,
        AttentionLevel.FOCUSED,
        AttentionLevel.FOCUSED,
    ]
    sample_df['Tags'] = ['Arcade', 'Story', 'Shooter', 'Logic', 'FPS']
    recommender = GameRecommender(sample_df)

    game = recommender.recommend(mood='zone_out')

    assert game['Name'] == 'Short Game'
    assert 'Mood: good for zoning out' in game['reasons']

def test_story_night_mood_prefers_story_games(sample_df):
    sample_df['attention_level'] = [
        AttentionLevel.CASUAL,
        AttentionLevel.FOCUSED,
        AttentionLevel.CASUAL,
        AttentionLevel.CASUAL,
        AttentionLevel.CASUAL,
    ]
    recommender = GameRecommender(sample_df)

    game = recommender.recommend(mood='story_night')

    assert game['Name'] == 'Long Game'
    assert 'Mood: focused story session' in game['reasons']

def test_mood_does_not_override_explicit_attention_filter(sample_df):
    sample_df['attention_level'] = [
        AttentionLevel.CASUAL,
        AttentionLevel.FOCUSED,
        AttentionLevel.FOCUSED,
        AttentionLevel.FOCUSED,
        AttentionLevel.FOCUSED,
    ]
    recommender = GameRecommender(sample_df)

    game = recommender.recommend(mood='zone_out', attention_level='focused')

    assert game['attention_level'] == AttentionLevel.FOCUSED

MOOD_SCORING_CASES = [
    pytest.param(
        "zone_out",
        [
            {"Name": "Chill Builder", "Genre": "Simulation", "Tags": "Relaxing;City Builder"},
            {"Name": "Generic Game", "Genre": "Action", "Tags": "Shooter"},
        ],
        "Chill Builder",
        id="zone_out_prefers_relaxing_city_builder_tags",
    ),
    pytest.param(
        "story_night",
        [
            {"Name": "Story Weaver", "Genre": "RPG", "Tags": "Story Rich;Choices Matter"},
            {"Name": "Gun Fight", "Genre": "Action", "Tags": "Shooter"},
        ],
        "Story Weaver",
        id="story_night_prefers_narrative_tags",
    ),
    pytest.param(
        "short_session",
        [
            {"Name": "Quick Puzzle", "Genre": "Puzzle", "Tags": "Puzzle", "Average_Playtime": 120},
            {"Name": "Long Puzzle", "Genre": "Puzzle", "Tags": "Puzzle", "Average_Playtime": 3600},
        ],
        "Quick Puzzle",
        id="short_session_prefers_short_hltb_over_identical_tags",
    ),
    pytest.param(
        "short_session",
        [
            {"Name": "Big RPG", "Genre": "RPG", "Tags": "Adventure", "Average_Playtime": 1500},
            {"Name": "Mystery Game", "Genre": "RPG", "Tags": "Adventure", "Average_Playtime": 0},
        ],
        "Mystery Game",
        id="short_session_long_game_penalty_loses_to_no_hltb_data",
    ),
    pytest.param(
        "finish_something",
        [
            {
                "Name": "Almost Done",
                "Playtime_Forever": 60,
                "Average_Playtime": 240,
                "status": GameStatus.PLAYING,
            },
            {
                "Name": "Just Started",
                "Playtime_Forever": 60,
                "Average_Playtime": 4860,
                "status": GameStatus.PLAYING,
            },
        ],
        "Almost Done",
        id="finish_something_prefers_less_remaining_time",
    ),
]

@pytest.mark.parametrize("mood, games, expected_winner", MOOD_SCORING_CASES)
def test_mood_scoring_picks_expected_winner(mood, games, expected_winner):
    defaults = {
        "Playtime_Forever": 0,
        "Average_Playtime": 0,
        "Genre": "",
        "Tags": "",
        "status": GameStatus.LIBRARY,
        "attention_level": AttentionLevel.UNSET,
    }
    rows = []
    for i, game in enumerate(games):
        row = {**defaults, **game}
        row["AppID"] = i + 1
        rows.append(row)
    df = pd.DataFrame(rows)
    recommender = GameRecommender(df)

    result = recommender.recommend(mood=mood)

    assert result['Name'] == expected_winner
