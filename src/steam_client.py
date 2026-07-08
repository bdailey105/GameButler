import httpx
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

async def fetch_game_details(app_id: int) -> Optional[Dict]:
    """
    Fetches game details from the Steam Store API.
    Returns a dictionary with 'genres', 'categories', 'header_image', 'short_description'.
    Returns None if the game is not found or an error occurs.
    """
    url = f"http://store.steampowered.com/api/appdetails?appids={app_id}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            
            if response.status_code == 429:
                logger.warning(f"Rate limit hit for AppID {app_id}")
                return None # Caller should handle backoff
                
            response.raise_for_status()
            
            data = response.json()
            
            # Steam API returns { "app_id": { "success": true, "data": { ... } } }
            app_data = data.get(str(app_id), {})
            if not app_data.get("success"):
                logger.warning(f"Steam API reported failure for AppID {app_id}")
                return None
                
            details = app_data.get("data", {})
            
            # Extract relevant fields
            genres = [g["description"] for g in details.get("genres", [])]
            categories = [c["description"] for c in details.get("categories", [])]
            
            return {
                "genres": genres,
                "categories": categories,
                "header_image": details.get("header_image"),
                "short_description": details.get("short_description")
            }
            
    except httpx.RequestError as e:
        logger.error(f"Network error fetching details for {app_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching details for {app_id}: {e}")
        return None

async def fetch_owned_games(api_key: str, steam_id: str) -> Optional[List[Dict]]:
    """
    Fetches the list of owned games for a Steam user from the Steam Web API.
    Returns a list of dictionaries with 'appid', 'name', 'playtime_forever'.
    Returns None if the profile is private, the steam_id is invalid, or an error occurs.
    """
    url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
    params = {
        "key": api_key,
        "steamid": steam_id,
        "include_appinfo": 1,
        "include_played_free_games": 1,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)

            response.raise_for_status()

            data = response.json()

            response_data = data.get("response", {})
            if "games" not in response_data:
                logger.warning(f"No games found for Steam ID {steam_id}. Profile may be private.")
                return None

            return response_data["games"]

    except httpx.HTTPStatusError as e:
        # Don't log the exception itself: its message contains the request URL with the API key
        logger.error(f"Steam API HTTP {e.response.status_code} fetching owned games for {steam_id}")
        return None
    except httpx.RequestError as e:
        # Log the error type only: httpx messages can embed the request URL with the API key
        logger.error(f"Network error ({type(e).__name__}) fetching owned games for {steam_id}")
        return None
    except Exception:
        logger.exception(f"Unexpected error fetching owned games for {steam_id}")
        return None
