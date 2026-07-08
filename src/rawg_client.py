import httpx
import logging
import os
from typing import Optional, Dict

logger = logging.getLogger(__name__)

async def search_game(name: str) -> Optional[Dict]:
    """
    Searches RAWG for a game by name.
    Returns a dictionary with 'header_image' and 'genres'.
    Returns None if RAWG isn't configured, no match is found, or an error occurs.
    """
    api_key = os.getenv("RAWG_API_KEY")
    if not api_key:
        return None

    url = "https://api.rawg.io/api/games"
    params = {
        "key": api_key,
        "search": name,
        "page_size": 1,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)

            response.raise_for_status()

            data = response.json()

            results = data.get("results", [])
            if not results:
                return None

            result = results[0]

            return {
                "header_image": result.get("background_image"),
                "genres": [g["name"] for g in result.get("genres", [])],
            }

    except httpx.HTTPStatusError as e:
        # Don't log the exception itself: its message contains the request URL with the API key
        logger.error(f"RAWG API HTTP {e.response.status_code} searching for {name}")
        return None
    except httpx.RequestError as e:
        # Log the error type only: httpx messages can embed the request URL with the API key
        logger.error(f"Network error ({type(e).__name__}) searching RAWG for {name}")
        return None
    except Exception:
        logger.exception(f"Unexpected error searching RAWG for {name}")
        return None
