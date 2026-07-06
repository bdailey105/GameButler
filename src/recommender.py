import pandas as pd
from typing import Optional
from src.models import GameStatus, AttentionLevel

class GameRecommender:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def recommend(self, 
                  genre: Optional[str] = None, 
                  tag: Optional[str] = None, 
                  unplayed_only: bool = False,
                  min_length: Optional[int] = None,
                  max_length: Optional[int] = None,
                  attention_level: Optional[str] = None,
                  mood: Optional[str] = None
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
        """
        if self.df.empty:
            return None
            
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
            return None

        scored_df = self.score_games(
            filtered_df,
            genre=genre,
            tag=tag,
            unplayed_only=unplayed_only,
            min_length=min_length,
            max_length=max_length,
            attention_level=attention_level,
            mood=mood,
        )
        return scored_df.iloc[0]

    def score_games(self,
                    df: pd.DataFrame,
                    genre: Optional[str] = None,
                    tag: Optional[str] = None,
                    unplayed_only: bool = False,
                    min_length: Optional[int] = None,
                    max_length: Optional[int] = None,
                    attention_level: Optional[str] = None,
                    mood: Optional[str] = None
                    ) -> pd.DataFrame:
        """Score already-filtered games using deterministic concierge signals."""
        scored = df.copy()
        scored["_score"] = 0
        scored["_reasons"] = [[] for _ in range(len(scored))]

        def add_reason(mask, points: int, reason: str):
            scored.loc[mask, "_score"] += points
            for idx in scored.index[mask]:
                scored.at[idx, "_reasons"] = scored.at[idx, "_reasons"] + [reason]

        if "status" in scored.columns:
            status = self.normalize_values(scored["status"])
            add_reason(status == GameStatus.UP_NEXT.value, 30, "Already in your Up Next queue")
            add_reason(status == GameStatus.PLAYING.value, 12, "You have already started it")

        if attention_level and "attention_level" in scored.columns:
            add_reason(self.normalize_values(scored["attention_level"]) == attention_level, 25, f"Matches your {attention_level} attention setting")

        if unplayed_only:
            add_reason(scored["Playtime_Forever"] == 0, 15, "You asked for something unplayed")
        else:
            add_reason(scored["Playtime_Forever"] > 0, 8, "You have some history with it")
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
            self.apply_mood_score(scored, add_reason, mood)

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

    def apply_mood_score(self, scored: pd.DataFrame, add_reason, mood: str):
        empty = pd.Series("", index=scored.index)
        zero = pd.Series(0, index=scored.index)
        genre_tags = scored.get("Genre", empty).astype(str) + " " + scored.get("Tags", empty).astype(str)
        attention = self.normalize_values(scored.get("attention_level", empty))
        playtime = scored.get("Playtime_Forever", zero)
        average = scored.get("Average_Playtime", zero)
        status = self.normalize_values(scored.get("status", empty))

        if mood == "zone_out":
            add_reason(attention == AttentionLevel.CASUAL.value, 20, "Mood: good for zoning out")
            add_reason(genre_tags.str.contains("Casual|Arcade|Roguelike|Simulation|Farming", case=False, na=False), 12, "Mood: low-friction tags")
        elif mood == "story_night":
            add_reason(attention == AttentionLevel.FOCUSED.value, 20, "Mood: focused story session")
            add_reason(genre_tags.str.contains("Story|RPG|Adventure|Narrative", case=False, na=False), 12, "Mood: story-friendly genre or tags")
        elif mood == "short_session":
            add_reason(average.between(1, 300), 22, "Mood: fits a short session")
            add_reason(genre_tags.str.contains("Roguelike|Arcade|Puzzle|Casual", case=False, na=False), 8, "Mood: easy to play in bursts")
        elif mood == "finish_something":
            add_reason(status.isin([GameStatus.PLAYING.value, GameStatus.UP_NEXT.value]), 20, "Mood: already on your active list")
            add_reason(playtime > 0, 12, "Mood: you have already made progress")
        elif mood == "surprise_me":
            add_reason(pd.Series(True, index=scored.index), 3, "Mood: surprise pick from eligible games")

    def recommend_random(self) -> Optional[pd.Series]:
        """Returns a random game from the library."""
        return self.recommend()

    def recommend_unplayed(self) -> Optional[pd.Series]:
        """Returns a random game with 0 playtime."""
        return self.recommend(unplayed_only=True)
