import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_get_champion_analysis_returns_data():
    mock_response = {"win_rate": 52.3, "tier": "A", "counters": [], "synergies": [], "recommended_builds": []}
    with patch("backend.draft.opgg_client._call_opgg_mcp", new_callable=AsyncMock, return_value=mock_response):
        from backend.draft.opgg_client import get_champion_analysis
        result = await get_champion_analysis("Rumble", "TOP")
    assert result["win_rate"] == 52.3
    assert "tier" in result


@pytest.mark.asyncio
async def test_get_champion_analysis_cache_hit():
    from backend.draft.opgg_client import _cache, get_champion_analysis
    _cache.clear()
    mock_response = {"win_rate": 50.0}
    with patch("backend.draft.opgg_client._call_opgg_mcp", new_callable=AsyncMock, return_value=mock_response) as mock_call:
        await get_champion_analysis("Garen", "TOP")
        await get_champion_analysis("Garen", "TOP")
    assert mock_call.call_count == 1


@pytest.mark.asyncio
async def test_get_matchup_returns_data():
    mock_response = {"laning_strength": 55.0, "early_advantage": "good", "tips": ["trade at level 3"]}
    with patch("backend.draft.opgg_client._call_opgg_mcp", new_callable=AsyncMock, return_value=mock_response):
        from backend.draft.opgg_client import get_matchup
        result = await get_matchup("Rumble", "Darius", "TOP")
    assert result["laning_strength"] == 55.0


@pytest.mark.asyncio
async def test_get_runes_returns_data():
    mock_response = {"primary_path": "Precision", "primary_runes": [8005, 9101], "secondary_path": "Sorcery", "secondary_runes": [8234, 8210], "shards": [5005, 5002, 5001]}
    with patch("backend.draft.opgg_client._call_opgg_mcp", new_callable=AsyncMock, return_value=mock_response):
        from backend.draft.opgg_client import get_runes
        result = await get_runes("Rumble", "TOP")
    assert result["primary_path"] == "Precision"
    assert len(result["shards"]) == 3


@pytest.mark.asyncio
async def test_cache_expires_after_ttl():
    import time
    from backend.draft.opgg_client import _cache, get_champion_analysis, CACHE_TTL_SECONDS
    _cache.clear()
    mock_response = {"win_rate": 50.0}
    with patch("backend.draft.opgg_client._call_opgg_mcp", new_callable=AsyncMock, return_value=mock_response) as mock_call:
        await get_champion_analysis("Zed", "MID")
        # Manually expire cache
        key = "champion_analysis:ZED:mid"
        old_ts, old_val = _cache[key]
        _cache[key] = (old_ts - CACHE_TTL_SECONDS - 1, old_val)
        await get_champion_analysis("Zed", "MID")
    assert mock_call.call_count == 2
