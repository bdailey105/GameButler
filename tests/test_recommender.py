import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta
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

def test_recommend_many_returns_n_distinct_games_sorted_descending(sample_df):
    sample_df['status'] = [GameStatus.LIBRARY] * len(sample_df)
    recommender = GameRecommender(sample_df)

    rows = recommender.recommend_many(3, mood='story_night')

    assert len(rows) == 3
    names = [row['Name'] for row in rows]
    assert len(set(names)) == 3
    scores = [row['score'] for row in rows]
    assert scores == sorted(scores, reverse=True)

def test_recommend_many_first_result_matches_recommend(sample_df):
    sample_df['status'] = [
        GameStatus.LIBRARY,
        GameStatus.UP_NEXT,
        GameStatus.LIBRARY,
        GameStatus.LIBRARY,
        GameStatus.LIBRARY,
    ]
    recommender = GameRecommender(sample_df)

    single = recommender.recommend()
    many = recommender.recommend_many(3)

    assert many[0]['Name'] == single['Name']

def test_mood_dominance_untagged_queue_game_loses_to_mood_match():
    df = pd.DataFrame([
        {
            "AppID": 1,
            "Name": "Queued But Mismatched",
            "Playtime_Forever": 0,
            "Average_Playtime": 0,
            "Genre": "Action",
            "Tags": "Shooter",
            "status": GameStatus.UP_NEXT,
            "attention_level": AttentionLevel.UNSET,
        },
        {
            "AppID": 2,
            "Name": "Story Match Not Queued",
            "Playtime_Forever": 0,
            "Average_Playtime": 0,
            "Genre": "RPG",
            "Tags": "Story Rich;Choices Matter",
            "status": GameStatus.LIBRARY,
            "attention_level": AttentionLevel.FOCUSED,
        },
    ])
    recommender = GameRecommender(df)

    result = recommender.recommend(mood='story_night')

    assert result['Name'] == 'Story Match Not Queued'

FEEDBACK_DEFAULTS = {
    "Playtime_Forever": 0,
    "Average_Playtime": 0,
    "Genre": "Action",
    "Tags": "Indie",
    "status": GameStatus.LIBRARY,
    "attention_level": AttentionLevel.UNSET,
}

def _feedback_df(games):
    rows = []
    for i, game in enumerate(games):
        row = {**FEEDBACK_DEFAULTS, **game}
        row.setdefault("AppID", i + 1)
        rows.append(row)
    return pd.DataFrame(rows)

SESSION_DEFAULTS = {
    "Playtime_Forever": 0,
    "Average_Playtime": 0,
    "Genre": "Action",
    "Tags": "Indie",
    "status": GameStatus.LIBRARY,
    "attention_level": AttentionLevel.UNSET,
    "session_tags": None,
}

def _session_df(games):
    rows = []
    for i, game in enumerate(games):
        row = {**SESSION_DEFAULTS, **game}
        row.setdefault("AppID", i + 1)
        rows.append(row)
    return pd.DataFrame(rows)

def test_available_minutes_completable_beats_unknown_length():
    df = _session_df([
        {"Name": "Completable", "Average_Playtime": 90},
        {"Name": "Unknown Length", "Average_Playtime": 0},
    ])
    recommender = GameRecommender(df)

    game = recommender.recommend(available_minutes=120)

    assert game['Name'] == "Completable"
    assert "Session: finishable tonight (~2h to beat)" in game['reasons']

def test_available_minutes_unknown_length_confidence_penalty():
    df = _session_df([{"Name": "Unknown Length", "Average_Playtime": 0}])
    recommender = GameRecommender(df)

    game = recommender.recommend(available_minutes=60)

    # +5 "Fresh start from your library" (unplayed default) - 4 confidence penalty
    assert game['score'] == 1
    assert not any(reason.startswith("Session: finishable") for reason in game['reasons'])

def test_explicit_length_filter_takes_precedence_over_session_input():
    df = _session_df([
        {"Name": "Fits Session Only", "Average_Playtime": 90},
        {"Name": "Fits Both", "Average_Playtime": 50},
    ])
    recommender = GameRecommender(df)

    rows = recommender.recommend_many(5, max_length=60, available_minutes=120)

    names = [row['Name'] for row in rows]
    assert names == ["Fits Both"]

def test_energy_low_favors_casual_tagged_game():
    df = _session_df([
        {"Name": "Casual Game", "attention_level": AttentionLevel.CASUAL},
        {"Name": "Focused Game", "attention_level": AttentionLevel.FOCUSED},
    ])
    recommender = GameRecommender(df)

    game = recommender.recommend(energy="low")

    assert game['Name'] == "Casual Game"
    assert "Session: low-energy friendly" in game['reasons']

def test_context_podcast_penalizes_story_rich_vs_grind_sibling():
    df = _session_df([
        {"Name": "Grind Fest", "Genre": "Simulation", "Tags": "Grinding"},
        {"Name": "Story Epic", "Genre": "RPG", "Tags": "Story Rich"},
    ])
    recommender = GameRecommender(df)

    game = recommender.recommend(context="podcast")

    assert game['Name'] == "Grind Fest"
    assert "Session: podcast-friendly grind" in game['reasons']

def test_burst_friendly_override_wins_at_30_minutes():
    df = _session_df([
        {"Name": "Tagged Burst", "session_tags": "burst_friendly"},
        {"Name": "Untagged Twin", "session_tags": None},
    ])
    recommender = GameRecommender(df)

    game = recommender.recommend(available_minutes=30)

    assert game['Name'] == "Tagged Burst"
    assert "Session: you marked this burst-friendly" in game['reasons']

def test_untagged_game_gets_no_session_suitability_reasons():
    df = _session_df([{"Name": "Untagged", "session_tags": None}])
    recommender = GameRecommender(df)

    game = recommender.recommend(available_minutes=30, context="couch")

    assert not any("you marked this" in reason for reason in game['reasons'])

def test_deferred_game_loses_to_otherwise_identical_game():
    df = _feedback_df([
        {"AppID": 1, "Name": "Deferred Game"},
        {"AppID": 2, "Name": "Untouched Game"},
    ])
    feedback = [{
        "game_id": 1,
        "decision": "deferred",
        "tags_snapshot": "Indie",
        "created_at": datetime.now(timezone.utc) - timedelta(days=2),
    }]
    recommender = GameRecommender(df, feedback=feedback)

    result = recommender.recommend()

    assert result['Name'] == 'Untouched Game'

def test_rejected_penalty_applies_within_window():
    df = _feedback_df([{"AppID": 1, "Name": "Rejected Game"}])
    baseline_score = GameRecommender(df).recommend()['score']

    feedback = [{
        "game_id": 1,
        "decision": "rejected",
        "tags_snapshot": "Indie",
        "created_at": datetime.now(timezone.utc) - timedelta(days=10),
    }]
    recommender = GameRecommender(df, feedback=feedback)

    result = recommender.recommend()

    assert result['score'] == baseline_score - 20

def test_expired_deferred_decision_has_no_effect():
    df = _feedback_df([
        {"AppID": 1, "Name": "Game A"},
        {"AppID": 2, "Name": "Game B"},
    ])
    feedback = [{
        "game_id": 1,
        "decision": "deferred",
        "tags_snapshot": "Indie",
        "created_at": datetime.now(timezone.utc) - timedelta(days=20),
    }]
    recommender = GameRecommender(df, feedback=feedback)

    rows = recommender.recommend_many(2)
    scores = {row['Name']: row['score'] for row in rows}

    assert scores["Game A"] == scores["Game B"]

def test_more_like_this_boosts_decided_game_and_tag_sibling():
    df = _feedback_df([
        {"AppID": 1, "Name": "Decided Game", "Tags": "Roguelike;Indie"},
        {"AppID": 2, "Name": "Tag Sibling", "Tags": "Roguelike;Adventure"},
        {"AppID": 3, "Name": "Unrelated Game", "Tags": "Puzzle"},
    ])
    feedback = [{
        "game_id": 1,
        "decision": "more_like_this",
        "tags_snapshot": "Roguelike;Indie",
        "game_name": "Decided Game",
        "created_at": datetime.now(timezone.utc) - timedelta(days=1),
    }]
    recommender = GameRecommender(df, feedback=feedback)

    rows = recommender.recommend_many(3)
    by_name = {row['Name']: row for row in rows}

    assert rows[0]['Name'] == 'Decided Game'
    assert any(r.startswith("Feedback:") for r in by_name['Decided Game']['reasons'])
    assert "Feedback: you asked for more like this" in by_name['Decided Game']['reasons']
    assert "Feedback: more like Decided Game" in by_name['Tag Sibling']['reasons']
    assert by_name['Tag Sibling']['score'] > by_name['Unrelated Game']['score']

def test_less_like_this_penalizes_tag_sibling():
    df = _feedback_df([
        {"AppID": 1, "Name": "Decided Game", "Tags": "Roguelike;Indie"},
        {"AppID": 2, "Name": "Tag Sibling", "Tags": "Roguelike;Adventure"},
        {"AppID": 3, "Name": "Unrelated Game", "Tags": "Puzzle"},
    ])
    feedback = [{
        "game_id": 1,
        "decision": "less_like_this",
        "tags_snapshot": "Roguelike;Indie",
        "created_at": datetime.now(timezone.utc) - timedelta(days=1),
    }]
    recommender = GameRecommender(df, feedback=feedback)

    rows = recommender.recommend_many(3)
    by_name = {row['Name']: row for row in rows}

    assert by_name['Unrelated Game']['score'] == by_name['Tag Sibling']['score'] + 6
    assert by_name['Decided Game']['score'] == by_name['Unrelated Game']['score'] - 10
