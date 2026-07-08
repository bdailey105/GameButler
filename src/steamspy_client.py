import httpx
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

async def fetch_user_tags(app_id: int) -> Optional[List[str]]:
    """
    Fetches community tags from the SteamSpy API.
    Returns the top 10 tags (by votes) sorted descending.
    Returns [] if SteamSpy has no tags for this app.
    Returns None if a transient error occurs (network/HTTP/unexpected).
    """
    url = "https://steamspy.com/api.php"
    params = {"request": "appdetails", "appid": app_id}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()

            data = response.json()

            # SteamSpy quirk: "tags" is a dict of {tag_name: votes} when present,
            # or an empty list [] when there are none.
            tags = data.get("tags")
            if not isinstance(tags, dict):
                return []

            sorted_tags = sorted(tags.items(), key=lambda item: item[1], reverse=True)
            return [name for name, _ in sorted_tags[:10]]

    except httpx.HTTPStatusError as e:
        logger.error(f"SteamSpy API HTTP {e.response.status_code} fetching tags for {app_id}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Network error ({type(e).__name__}) fetching tags for {app_id}")
        return None
    except Exception:
        logger.exception(f"Unexpected error fetching tags for {app_id}")
        return None
