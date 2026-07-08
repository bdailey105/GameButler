import httpx
import logging
import os
from typing import Optional, Dict
from urllib.parse import quote

logger = logging.getLogger(__name__)

BASE_URL = "https://www.steamgriddb.com/api/v2"

async def search_game(name: str) -> Optional[Dict]:
    """
    Searches SteamGridDB for a game by name and fetches header-style art.
    Returns a dictionary with 'header_image' and 'genres' (always empty —
    SteamGridDB is art-only).
    Returns None if not configured, no match is found, or an error occurs.
    """
    api_key = os.getenv("STEAMGRIDDB_API_KEY")
    if not api_key:
        return None

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            response = await client.get(f"{BASE_URL}/search/autocomplete/{quote(name, safe='')}")
            response.raise_for_status()
            results = response.json().get("data", [])
            if not results:
                return None

            game_id = results[0]["id"]

            # 460x215/920x430 grids match the Steam header aspect the UI is styled for
            grids = await client.get(f"{BASE_URL}/grids/game/{game_id}", params={"dimensions": "460x215,920x430"})
            grids.raise_for_status()
            grid_data = grids.json().get("data", [])

            if not grid_data:
                # Fall back to any grid style rather than no art at all
                grids = await client.get(f"{BASE_URL}/grids/game/{game_id}")
                grids.raise_for_status()
                grid_data = grids.json().get("data", [])

            if not grid_data:
                return None

            return {"header_image": grid_data[0]["url"], "genres": []}

    except httpx.HTTPStatusError as e:
        logger.error(f"SteamGridDB HTTP {e.response.status_code} searching for {name}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Network error ({type(e).__name__}) searching SteamGridDB for {name}")
        return None
    except Exception:
        logger.exception(f"Unexpected error searching SteamGridDB for {name}")
        return None
