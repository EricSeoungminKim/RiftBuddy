from unittest.mock import AsyncMock, patch

import pytest

from backend.riot.live_client import GameState, fetch_game_state


@pytest.mark.asyncio
async def test_fetch_game_state_returns_game_state():
    mock_response = {
        "activePlayer": {
            "championStats": {"currentHealth": 1200, "maxHealth": 2000},
            "currentGold": 1500,
            "level": 8,
            "riotId": "LEGENO#2026",
            "summonerName": "LEGENO#2026",
        },
        "allPlayers": [
            {
                "championName": "Rumble",
                "riotId": "LEGENO#2026",
                "summonerName": "LEGENO#2026",
                "scores": {
                    "kills": 2,
                    "deaths": 1,
                    "assists": 3,
                    "creepScore": 64,
                    "wardScore": 5.0,
                },
                "items": [{"displayName": "Doran's Shield"}],
                "summonerSpells": {
                    "summonerSpellOne": {"displayName": "Ignite"},
                    "summonerSpellTwo": {"displayName": "Flash"},
                },
            }
        ],
        "events": {"Events": []},
        "gameData": {"gameTime": 420.0, "gameMode": "PRACTICETOOL"},
    }
    with patch.dict("backend.riot.live_client.CONFIG", {"test_mode": "0"}), patch(
        "backend.riot.live_client._get", new=AsyncMock(return_value=mock_response)
    ):
        state = await fetch_game_state()
    assert isinstance(state, GameState)
    assert state.current_health == 1200
    assert state.gold == 1500
    assert state.level == 8
    assert state.game_time == 420.0
    assert state.champion_name == "Rumble"
    assert state.creep_score == 64
    assert state.kills == 2
    assert state.items == ("Doran's Shield",)


@pytest.mark.asyncio
async def test_fetch_game_state_returns_none_when_client_down():
    with patch.dict("backend.riot.live_client.CONFIG", {"test_mode": "0"}), patch(
        "backend.riot.live_client._get", new=AsyncMock(side_effect=Exception("Connection refused"))
    ):
        state = await fetch_game_state()
    assert state is None


@pytest.mark.asyncio
async def test_fetch_game_state_returns_fake_state_in_test_mode():
    with patch.dict("backend.riot.live_client.CONFIG", {"test_mode": "1"}):
        state = await fetch_game_state()

    assert isinstance(state, GameState)
    assert state.gold == 2750
