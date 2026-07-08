import pytest
from unittest.mock import patch, MagicMock
from src.steam_client import fetch_game_details

@pytest.mark.asyncio
async def test_fetch_game_details_success():
    mock_response = {
        "1086940": {
            "success": True,
            "data": {
                "name": "Baldur's Gate 3",
                "genres": [{"description": "RPG"}, {"description": "Strategy"}],
                "categories": [{"description": "Single-player"}, {"description": "Co-op"}],
                "header_image": "http://example.com/bg3.jpg",
                "short_description": "An amazing RPG."
            }
        }
    }
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_response,
            raise_for_status=lambda: None
        )
        
        result = await fetch_game_details(1086940)
        
        assert result is not None
        assert "RPG" in result["genres"]
        assert "Single-player" in result["categories"]
        assert result["header_image"] == "http://example.com/bg3.jpg"

@pytest.mark.asyncio
async def test_fetch_game_details_failure():
    mock_response = {
        "999999": {
            "success": False
        }
    }
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_response,
            raise_for_status=lambda: None
        )
        
        result = await fetch_game_details(999999)
        # {} = permanent "no store page" (delisted); None is reserved for transient errors
        assert result == {}
