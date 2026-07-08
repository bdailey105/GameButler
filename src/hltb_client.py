import logging
from typing import Optional

from howlongtobeatpy import HowLongToBeat

logger = logging.getLogger(__name__)

async def fetch_time_to_beat(name: str) -> Optional[int]:
    """
    Looks up the "main story" time-to-beat for a game on HowLongToBeat.
    Returns minutes to beat the main story, 0 if HLTB has no data for this
    game (searched, nothing found), or None on an unexpected/transient error
    (caller should treat this as "not yet looked up" and retry later).
    """
    try:
        results = await HowLongToBeat().async_search(name)

        if not results:
            return 0

        best = max(results, key=lambda entry: entry.similarity)

        if not best.main_story:
            return 0

        return int(best.main_story * 60)

    except Exception as e:
        logger.error(f"Unexpected error fetching time-to-beat for {name}: {e}")
        return None
