from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.main import app, _game_state_to_ws_payload
from backend.riot.live_client import GameState


def test_backend_allows_vite_renderer_cors():
    with TestClient(app) as client:
        response = client.options(
            "/lcu/champ-select/status",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_game_state_to_ws_payload_shape():
    state = GameState(
        current_health=1450.0,
        max_health=2000.0,
        gold=2750.0,
        level=9,
        game_time=720.0,
        champion_name="Renekton",
        assigned_position="TOP",
        kills=3,
        deaths=1,
        assists=2,
        creep_score=72,
    )
    payload = _game_state_to_ws_payload(state)
    assert payload["type"] == "game_state"
    assert payload["gameTime"] == 720.0
    assert payload["championName"] == "Renekton"
    assert payload["position"] == "TOP"
    assert payload["health"] == 1450.0
    assert payload["maxHealth"] == 2000.0
    assert payload["gold"] == 2750.0
    assert payload["level"] == 9
    assert payload["kills"] == 3
    assert payload["deaths"] == 1
    assert payload["assists"] == 2
    assert payload["cs"] == 72
    assert isinstance(payload["items"], list)
    assert isinstance(payload["allyChampions"], list)
    assert isinstance(payload["enemyChampions"], list)


def test_websocket_planned_action_sends_generated_question():
    state = GameState(
        current_health=900,
        max_health=1000,
        gold=700,
        level=8,
        game_time=600,
        gold_diff=2200,
    )

    with patch.dict("backend.main.CONFIG", {"test_mode": "0", "bypass_auth": "1", "response_language": "ko"}), patch(
        "backend.main.fetch_game_state", new=AsyncMock(return_value=state)
    ), patch(
        "backend.main.get_advice", new=AsyncMock(return_value="리드를 굳히려면 시야를 잡고 오브젝트를 준비하세요.")
    ):
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as websocket:
                websocket.send_json({"mode": "planned", "query": None, "language": "ko"})

                transcript = websocket.receive_json()
                advice = websocket.receive_json()

    assert transcript["type"] == "transcript"
    assert "앞서는 상황" in transcript["text"]
    assert advice["type"] == "advice"
