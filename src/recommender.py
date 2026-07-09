import pandas as pd
from typing import Optional
from datetime import datetime, timezone
from src.models import GameStatus, AttentionLevel

def _format_hours(minutes) -> str:
    """Render a minutes value as a human-friendly hours label, e.g. '5h' or '<1h'."""
    hours = round((minutes or 0) / 60)
    return "<1h" if hours == 0 else f"{hours}h"

class GameRecommender:
    def __init__(self, df: pd.DataFrame, feedback: Optional[list] = None):
        self.df = df
        self.feedback = feedback or []

    def recommend(self,
                  genre: Optional[str] = None,
                  tag: Optional[str] = None,
                  unplayed_only: bool = False,
                  min_length: Optional[int] = None,
                  max_length: Optional[int] = None,
                  attention_level: Optional[str] = None,
                  mood: Optional[str] = None,
                  available_minutes: Optional[int] = None,
                  energy: Optional[str] = None,
                  context: Optional[str] = None
                  ) -> Optional[pd.Series]:
        """
        Returns the highest-scoring game matching the criteria.

        Args:
            genre: Substring to match in the Genre column (case-insensitive).
            tag: Substring to match in the Tags column (case-insensitive).
            unplayed_only: If True, only considers games with 0 playtime.
            min_length: Minimum Average_Playtime (minutes).
            max_length: Maximum Average_Playtime (minutes).
            attention_level: Filter by specific attention level (casual, focused).
            available_minutes: Tonight's available session length (minutes); scoring only.
            energy: Tonight's energy level (low, medium, high); scoring only.
            context: Tonight's play context (desk, couch, handheld, podcast); scoring only.
        """
        rows = self.recommend_many(
            1,
            genre=genre,
            tag=tag,
            unplayed_only=unplayed_only,
            min_length=min_length,
            max_length=max_length,
            attention_level=attention_level,
            mood=mood,
            available_minutes=available_minutes,
            energy=energy,
            context=context,
        )
        return rows[0] if rows else None

    def recommend_many(self,
                        n: int = 1,
                        genre: Optional[str] = None,
                        tag: Optional[str] = None,
                        unplayed_only: bool = False,
                        min_length: Optional[int] = None,
                        max_length: Optional[int] = None,
                        attention_level: Optional[str] = None,
                        mood: Optional[str] = None,
                        available_minutes: Optional[int] = None,
                        energy: Optional[str] = None,
                        context: Optional[str] = None
                        ) -> list:
        """
        Returns up to n highest-scoring games matching the criteria, sorted best-first.

        Args:
            n: Maximum number of games to return.
            genre: Substring to match in the Genre column (case-insensitive).
            tag: Substring to match in the Tags column (case-insensitive).
            unplayed_only: If True, only considers games with 0 playtime.
            min_length: Minimum Average_Playtime (minutes).
            max_length: Maximum Average_Playtime (minutes).
            attention_level: Filter by specific attention level (casual, focused).
            available_minutes: Tonight's available session length (minutes); scoring only.
            energy: Tonight's energy level (low, medium, high); scoring only.
            context: Tonight's play context (desk, couch, handheld, podcast); scoring only.
        """
        if self.df.empty:
            return []

        filtered_df = self.df.copy()

        # Default Filter: Exclude Completed and Abandoned.
        # Assuming we want to play things we haven't finished or abandoned.
        if 'status' in filtered_df.columns:
            status = self.normalize_values(filtered_df['status'])
            filtered_df = filtered_df[~status.isin([GameStatus.COMPLETED.value, GameStatus.ABANDONED.value])]

        # Filter by playtime
        if unplayed_only:
            filtered_df = filtered_df[filtered_df['Playtime_Forever'] == 0]

        # Filter by genre
        if genre:
            filtered_df = filtered_df[filtered_df['Genre'].astype(str).str.contains(genre, case=False, na=False)]

        # Filter by tag
        if tag:
            filtered_df = filtered_df[filtered_df['Tags'].astype(str).str.contains(tag, case=False, na=False)]

        # Filter by length (Time to Beat)
        if 'Average_Playtime' in filtered_df.columns:
            if min_length is not None:
                filtered_df = filtered_df[filtered_df['Average_Playtime'] >= min_length]
            if max_length is not None:
                filtered_df = filtered_df[filtered_df['Average_Playtime'] <= max_length]

        # Filter by Attention Level
        if attention_level and 'attention_level' in filtered_df.columns:
            filtered_df = filtered_df[self.normalize_values(filtered_df['attention_level']) == attention_level]

        if filtered_df.empty:
            return []

        scored_df = self.score_games(
            filtered_df,
            genre=genre,
            tag=tag,
            unplayed_only=unplayed_only,
            min_length=min_length,
            max_length=max_length,
            attention_level=attention_level,
            mood=mood,
            available_minutes=available_minutes,
            energy=energy,
            context=context,
        )
        return [row for _, row in scored_df.head(n).iterrows()]

    def score_games(self,
                    df: pd.DataFrame,
                    genre: Optional[str] = None,
                    tag: Optional[str] = None,
                    unplayed_only: bool = False,
                    min_length: Optional[int] = None,
                    max_length: Optional[int] = None,
                    attention_level: Optional[str] = None,
                    mood: Optional[str] = None,
                    available_minutes: Optional[int] = None,
                    energy: Optional[str] = None,
                    context: Optional[str] = None
                    ) -> pd.DataFrame:
        """Score already-filtered games using deterministic concierge signals."""
        scored = df.copy()
        scored["_score"] = 0
        scored["_reasons"] = [[] for _ in range(len(scored))]

        def add_reason(mask, points: int, reason: str):
            scored.loc[mask, "_score"] += points
            for idx in scored.index[mask]:
                scored.at[idx, "_reasons"] = scored.at[idx, "_reasons"] + [reason]

        def add_score(mask, points: int):
            scored.loc[mask, "_score"] += points

        def add_dynamic_reason(mask, points: int, make_reason):
            scored.loc[mask, "_score"] += points
            for idx in scored.index[mask]:
                scored.at[idx, "_reasons"] = scored.at[idx, "_reasons"] + [make_reason(scored.loc[idx])]

        queue_pts, playing_pts, history_pts = (15, 6, 4) if mood else (30, 12, 8)

        if "status" in scored.columns:
            status = self.normalize_values(scored["status"])
            add_reason(status == GameStatus.UP_NEXT.value, queue_pts, "Already in your Up Next queue")
            add_reason(status == GameStatus.PLAYING.value, playing_pts, "You have already started it")

        if attention_level and "attention_level" in scored.columns:
            add_reason(self.normalize_values(scored["attention_level"]) == attention_level, 25, f"Matches your {attention_level} attention setting")

        if unplayed_only:
            add_reason(scored["Playtime_Forever"] == 0, 15, "You asked for something unplayed")
        else:
            add_dynamic_reason(
                scored["Playtime_Forever"] > 0,
                history_pts,
                lambda row: f"You've already put in {_format_hours(row['Playtime_Forever'])}",
            )
            add_reason(scored["Playtime_Forever"] == 0, 5, "Fresh start from your library")

        if genre:
            add_reason(scored["Genre"].astype(str).str.contains(genre, case=False, na=False), 10, f"Matches genre: {genre}")
        if tag:
            add_reason(scored["Tags"].astype(str).str.contains(tag, case=False, na=False), 10, f"Matches tag: {tag}")

        if "Average_Playtime" in scored.columns and (min_length is not None or max_length is not None):
            length_mask = pd.Series(True, index=scored.index)
            if min_length is not None:
                length_mask &= scored["Average_Playtime"] >= min_length
            if max_length is not None:
                length_mask &= scored["Average_Playtime"] <= max_length
            add_reason(length_mask, 10, "Fits your session length")

        if mood:
            self.apply_mood_score(scored, add_reason, add_score, add_dynamic_reason, mood)

        if available_minutes is not None or energy or context:
            self.apply_session_score(
                scored, add_reason, add_score, add_dynamic_reason,
                available_minutes=available_minutes, energy=energy, context=context,
            )

        self.apply_feedback_score(scored, add_reason, add_score)

        empty_reasons = scored["_reasons"].apply(len) == 0
        for idx in scored.index[empty_reasons]:
            scored.at[idx, "_reasons"] = ["Best deterministic fit from the current filters"]

        scored["score"] = scored["_score"]
        scored["reasons"] = scored["_reasons"]
        scored = scored.drop(columns=["_score", "_reasons"])
        sort_columns = ["score"]
        ascending = [False]
        if "Name" in scored.columns:
            sort_columns.append("Name")
            ascending.append(True)
        if "AppID" in scored.columns:
            sort_columns.append("AppID")
            ascending.append(True)
        return scored.sort_values(sort_columns, ascending=ascending)

    def normalize_values(self, series: pd.Series) -> pd.Series:
        return series.map(lambda value: getattr(value, "value", value)).astype(str)

    def apply_mood_score(self, scored: pd.DataFrame, add_reason, add_score, add_dynamic_reason, mood: str):
        empty = pd.Series("", index=scored.index)
        zero = pd.Series(0, index=scored.index)
        genre_tags = scored.get("Genre", empty).astype(str) + " " + scored.get("Tags", empty).astype(str)
        attention = self.normalize_values(scored.get("attention_level", empty))
        playtime = scored.get("Playtime_Forever", zero)
        average = scored.get("Average_Playtime", zero)
        status = self.normalize_values(scored.get("status", empty))

        if mood == "zone_out":
            add_reason(attention == AttentionLevel.CASUAL.value, 20, "Mood: good for zoning out")
            add_reason(genre_tags.str.contains("Casual|Arcade|Relaxing|Simulation|Farming|Sandbox|Building|City Builder|Management|Automation|Driving|Racing|Idle", case=False, na=False), 12, "Mood: low-friction tags")
        elif mood == "story_night":
            add_reason(attention == AttentionLevel.FOCUSED.value, 20, "Mood: focused story session")
            add_reason(genre_tags.str.contains("Story|RPG|Adventure|Narrative|Atmospheric|Choices Matter|Visual Novel|Walking Simulator|Mystery|Drama", case=False, na=False), 12, "Mood: story-friendly genre or tags")
        elif mood == "short_session":
            add_dynamic_reason(
                average.between(1, 300),
                22,
                lambda row: f"~{_format_hours(row['Average_Playtime'])} to beat — fits a short session",
            )
            add_score(average > 1200, -15)
            add_reason(genre_tags.str.contains("Roguelike|Roguelite|Arcade|Puzzle|Casual|Platformer|Card Game|Bullet Hell|Fast-Paced", case=False, na=False), 8, "Mood: easy to play in bursts")
        elif mood == "finish_something":
            add_reason(status.isin([GameStatus.PLAYING.value, GameStatus.UP_NEXT.value]), 20, "Mood: already on your active list")
            add_reason(playtime > 0, 12, "Mood: you have already made progress")
            remaining = (average - playtime).clip(lower=0)
            add_dynamic_reason(
                (average > 0) & (remaining <= 720),
                15,
                lambda row: f"~{_format_hours(max(row['Average_Playtime'] - row['Playtime_Forever'], 0))} left to finish",
            )
        elif mood == "surprise_me":
            add_reason(pd.Series(True, index=scored.index), 3, "Mood: surprise pick from eligible games")

    def apply_session_score(self, scored: pd.DataFrame, add_reason, add_score, add_dynamic_reason,
                             available_minutes: Optional[int] = None,
                             energy: Optional[str] = None,
                             context: Optional[str] = None):
        """Apply tonight's session-planning adjustments: available time, energy, and setting.

        These are score-only nudges — they never filter out a game. The explicit
        genre/tag/length/attention filters in recommend_many already ran before
        scoring begins, so they take precedence over session inputs by construction;
        session inputs can only reorder among games that already survived those filters.

        Effects:

        | Input              | Condition                                                | Effect                                                        |
        |--------------------|-----------------------------------------------------------|----------------------------------------------------------------|
        | available_minutes  | 0 < Average_Playtime <= available_minutes                  | +20, "Session: finishable tonight (~Xh to beat)"                |
        |                    | available_minutes <= 30 & burst-friendly tags               | +10, "Session: easy to dip into"                                |
        |                    | available_minutes <= 60 & Average_Playtime > 1200           | -12 (no reason; a caution, not a claim)                         |
        |                    | Average_Playtime is null or 0 (unknown)                     | -4 (confidence penalty; never claims a fit it can't know)       |
        | energy=low         | attention_level == casual                                   | +10, "Session: low-energy friendly"                             |
        |                    | Relaxing/Casual/Sandbox/Farming/Driving tags                 | +8, "Session: gentle tags for a tired night"                    |
        | energy=high        | attention_level == focused                                   | +10, "Session: worth your full focus"                           |
        |                    | Challenging/Difficult/Souls-like/Strategy tags                | +8, "Session: demands your A-game"                              |
        | energy=medium      | -                                                             | no adjustment                                                   |
        | context=desk       | Strategy/4X/Management/City Builder/Simulation tags           | +8, "Session: mouse-and-keyboard fit"                           |
        | context=couch      | Full controller support/Controller tags                       | +10, "Session: controller-friendly for the couch"               |
        | context=handheld   | 2D/Platformer/Card Game/Casual/Pixel tags                      | +8, "Session: handheld-friendly"                                |
        | context=podcast    | Grinding/Management/Simulation/Arcade/Racing/Sandbox tags       | +10, "Session: podcast-friendly grind"                          |
        |                    | Story Rich/Narrative/Visual Novel tags                          | -6 (no reason; dialogue-heavy fights the podcast)                |

        Suitability overrides (session_tags column, only applied when set and only when
        the matching session input is chosen — untagged games get nothing):

        | session_tags       | Condition                                | Effect                                                    |
        |--------------------|--------------------------------------------|--------------------------------------------------------------|
        | burst_friendly     | available_minutes <= 30                     | +15, "Session: you marked this burst-friendly"               |
        | controller_only    | context in (couch, handheld)                | +12, "Session: you marked this controller-ready"             |
        | podcast_friendly   | context == podcast                          | +15, "Session: you marked this podcast-friendly"             |
        """
        empty = pd.Series("", index=scored.index)
        zero = pd.Series(0, index=scored.index)
        genre_tags = scored.get("Genre", empty).astype(str) + " " + scored.get("Tags", empty).astype(str)
        attention = self.normalize_values(scored.get("attention_level", empty))
        average = scored.get("Average_Playtime", zero)
        session_tags = scored.get("session_tags", empty).astype(str)

        if available_minutes is not None:
            add_dynamic_reason(
                (average > 0) & (average <= available_minutes),
                20,
                lambda row: f"Session: finishable tonight (~{_format_hours(row['Average_Playtime'])} to beat)",
            )
            if available_minutes <= 30:
                add_reason(
                    genre_tags.str.contains("Roguelike|Roguelite|Arcade|Puzzle|Casual|Platformer|Card Game", case=False, na=False),
                    10,
                    "Session: easy to dip into",
                )
            if available_minutes <= 60:
                add_score(average > 1200, -12)
            add_score(average.isna() | (average == 0), -4)

        if energy == "low":
            add_reason(attention == AttentionLevel.CASUAL.value, 10, "Session: low-energy friendly")
            add_reason(genre_tags.str.contains("Relaxing|Casual|Sandbox|Farming|Driving", case=False, na=False), 8, "Session: gentle tags for a tired night")
        elif energy == "high":
            add_reason(attention == AttentionLevel.FOCUSED.value, 10, "Session: worth your full focus")
            add_reason(genre_tags.str.contains("Challenging|Difficult|Souls-like|Strategy", case=False, na=False), 8, "Session: demands your A-game")

        if context == "desk":
            add_reason(genre_tags.str.contains("Strategy|4X|Management|City Builder|Simulation", case=False, na=False), 8, "Session: mouse-and-keyboard fit")
        elif context == "couch":
            add_reason(genre_tags.str.contains("Full controller support|Controller", case=False, na=False), 10, "Session: controller-friendly for the couch")
        elif context == "handheld":
            add_reason(genre_tags.str.contains("2D|Platformer|Card Game|Casual|Pixel", case=False, na=False), 8, "Session: handheld-friendly")
        elif context == "podcast":
            add_reason(genre_tags.str.contains("Grinding|Management|Simulation|Arcade|Racing|Sandbox", case=False, na=False), 10, "Session: podcast-friendly grind")
            add_score(genre_tags.str.contains("Story Rich|Narrative|Visual Novel", case=False, na=False), -6)

        if available_minutes is not None and available_minutes <= 30:
            add_reason(session_tags.str.contains("burst_friendly", case=False, na=False), 15, "Session: you marked this burst-friendly")
        if context in ("couch", "handheld"):
            add_reason(session_tags.str.contains("controller_only", case=False, na=False), 12, "Session: you marked this controller-ready")
        if context == "podcast":
            add_reason(session_tags.str.contains("podcast_friendly", case=False, na=False), 15, "Session: you marked this podcast-friendly")

    def apply_feedback_score(self, scored: pd.DataFrame, add_reason, add_score):
        """Apply preference-learning adjustments from recent recommendation decisions.

        Effects, relative to `decision.created_at` (UTC), documented for transparency:

        | Decision        | Effect                                                                | Window  |
        |-----------------|------------------------------------------------------------------------|---------|
        | deferred        | decided game -25 (temporary deprioritization, not hidden)              | 7 days  |
        | rejected        | decided game -20                                                        | 14 days |
        | less_like_this  | decided game -10; primary-tag siblings -6                              | 30 days |
        | more_like_this  | decided game +10 ("Feedback: you asked for more like this");           | 30 days |
        |                 | primary-tag siblings +8 ("Feedback: more like {game_name}")            |         |

        Negative adjustments use add_score (no reason strings — reasons are shown as
        positives); positive adjustments use add_reason so feedback signals are
        visibly distinguished (prefixed "Feedback:") from mood/queue/metadata reasons.
        The "primary tag" is the first entry of a decision's tags_snapshot, matched as a
        case-insensitive substring against the Tags column; skipped when the snapshot is
        empty or "Unknown". Matching uses the AppID column against each decision's game_id.
        """
        if not self.feedback or "AppID" not in scored.columns:
            return

        now = datetime.now(timezone.utc)

        def age_days(created_at) -> float:
            if created_at is None:
                return float("inf")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            return (now - created_at).total_seconds() / 86400

        def primary_tag(tags_snapshot) -> Optional[str]:
            if not tags_snapshot:
                return None
            first = tags_snapshot.split(";")[0].strip()
            if not first or first.lower() == "unknown":
                return None
            return first

        for decision in self.feedback:
            age = age_days(decision.get("created_at"))
            mask_self = scored["AppID"] == decision.get("game_id")
            decision_type = decision.get("decision")

            if decision_type == "deferred" and age <= 7:
                add_score(mask_self, -25)
            elif decision_type == "rejected" and age <= 14:
                add_score(mask_self, -20)
            elif decision_type == "less_like_this" and age <= 30:
                add_score(mask_self, -10)
                tag = primary_tag(decision.get("tags_snapshot"))
                if tag and "Tags" in scored.columns:
                    sibling_mask = scored["Tags"].astype(str).str.contains(tag, case=False, na=False) & ~mask_self
                    add_score(sibling_mask, -6)
            elif decision_type == "more_like_this" and age <= 30:
                add_reason(mask_self, 10, "Feedback: you asked for more like this")
                tag = primary_tag(decision.get("tags_snapshot"))
                if tag and "Tags" in scored.columns:
                    sibling_mask = scored["Tags"].astype(str).str.contains(tag, case=False, na=False) & ~mask_self
                    game_name = decision.get("game_name") or "that game"
                    add_reason(sibling_mask, 8, f"Feedback: more like {game_name}")

    def recommend_random(self) -> Optional[pd.Series]:
        """Returns a random game from the library."""
        return self.recommend()

    def recommend_unplayed(self) -> Optional[pd.Series]:
        """Returns a random game with 0 playtime."""
        return self.recommend(unplayed_only=True)
