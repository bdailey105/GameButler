import pandas as pd
import os
import numpy as np

def load_steam_library(file_path: str) -> pd.DataFrame:
    """
    Loads the Steam library from a CSV file.
    Supports both the internal sample format and the user's provided export format.
    
    Args:
        file_path (str): Path to the CSV file.
        
    Returns:
        pd.DataFrame: DataFrame containing the game library with normalized columns:
                      [AppID, Name, Playtime_Forever, Genre, Tags, Average_Playtime]
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' was not found.")
    
    try:
        df = pd.read_csv(file_path)
        
        # Check for User Export Format (game, id, hours, ...)
        if 'game' in df.columns and 'id' in df.columns:
            # Rename columns
            df = df.rename(columns={
                'game': 'Name',
                'id': 'AppID',
                'hours': 'Playtime_Forever'
            })
            
            # Normalize Playtime
            # 'hours' column might be NaN. Fill with 0.
            df['Playtime_Forever'] = df['Playtime_Forever'].fillna(0)
            
            # Convert hours to minutes for consistency with internal logic
            # Assuming the input is in hours (float)
            df['Playtime_Forever'] = df['Playtime_Forever'] * 60
            
            # Add missing columns with defaults
            if 'Genre' not in df.columns:
                df['Genre'] = 'Unknown'
            if 'Tags' not in df.columns:
                df['Tags'] = 'Unknown'
            if 'Average_Playtime' not in df.columns:
                df['Average_Playtime'] = 0 # No time-to-beat data in this export
                
        # Basic cleaning for standard format
        # Ensure Playtime is numeric
        if 'Playtime_Forever' in df.columns:
             df['Playtime_Forever'] = pd.to_numeric(df['Playtime_Forever'], errors='coerce').fillna(0)

        # Ensure required columns exist
        required_cols = ['AppID', 'Name']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
                
        return df
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")

# Normalized external (non-Steam) library import format. See docs/import-format.md.
EXTERNAL_REQUIRED_HEADERS = ["title", "platform", "source"]
EXTERNAL_OPTIONAL_HEADERS = ["external_id", "genre", "tags", "playtime_minutes"]
# Steam is excluded on purpose: Steam has its own sync, so a "steam" row here is
# invalid rather than silently accepted.
EXTERNAL_VALID_PLATFORMS = {"switch", "playstation", "xbox", "pc", "retro"}

def load_external_library(file_path: str) -> pd.DataFrame:
    """
    Loads a normalized external (non-Steam) library CSV for import.

    Required headers (case-insensitive, whitespace-stripped): title, platform, source
    Optional headers: external_id, genre, tags, playtime_minutes

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        pd.DataFrame: DataFrame with lowercased column names, one row per input row.
                      Optional columns are added (filled with None) if absent.
                      Per-row validation (empty title, unsupported platform,
                      non-numeric playtime_minutes) happens at the API layer, not here.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' was not found.")

    try:
        df = pd.read_csv(file_path, dtype=str)
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")

    df.columns = [str(column).strip().lower() for column in df.columns]

    missing = [header for header in EXTERNAL_REQUIRED_HEADERS if header not in df.columns]
    if missing:
        raise ValueError(f"Missing required headers: {', '.join(missing)}")

    for optional in EXTERNAL_OPTIONAL_HEADERS:
        if optional not in df.columns:
            df[optional] = None

    return df