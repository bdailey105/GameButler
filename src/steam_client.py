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
