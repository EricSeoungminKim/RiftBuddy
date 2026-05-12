from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend import main as main_module
from backend.main import app, _fetch_riot_cs_snippet, _game_state_to_ws_payload, _record_session_snapshot
from backend.riot.live_client import GameState
from backend.stats.riot_cs_benchmarks import CsBenchmark


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


def test_record_session_snapshot_throttles_polling_snapshots():
    try:
        main_module._game_session.clear()
        main_module._last_session_snapshot_game_time = None
        first = GameState(current_health=1000, max_health=1000, gold=500, level=3, game_time=10)
        soon = GameState(current_health=900, max_health=1000, gold=550, level=3, game_time=20)
        later = GameState(current_health=800, max_health=1000, gold=650, level=4, game_time=41)

        assert _record_session_snapshot(first) is True
        assert _record_session_snapshot(soon) is False
        assert _record_session_snapshot(later) is True
        assert len(main_module._game_session.snapshots) == 2
    finally:
        main_module._game_session.clear()
        main_module._last_session_snapshot_game_time = None


def test_draft_context_endpoint_caches_lane_opponent():
    try:
        with TestClient(app) as client:
            response = client.post(
                "/game/draft-context",
                json={"my_champion": "Rumble", "my_position": "top", "lane_opponent": "Darius"},
            )

        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert main_module._cached_lane_opponent == "Darius"
        assert main_module._draft_context is not None
        assert main_module._draft_context.my_position == "TOP"
    finally:
        main_module._cached_lane_opponent = None
        main_module._lane_opponent_cache_key = ""
        main_module._draft_context = None


async def _fake_fetch_cs_benchmark(*args, **kwargs):
    return CsBenchmark(
        champion="Caitlyn",
        position="BOTTOM",
        tier="DIAMOND",
        region="KR",
        samples=10,
        avg_cspm=7.5,
        cs_at={"10": 75.0},
    )


@patch("backend.main.fetch_cs_benchmark", new=_fake_fetch_cs_benchmark)
def test_riot_cs_snippet_compares_current_cs_to_benchmark():
    import asyncio

    state = GameState(
        current_health=900,
        max_health=1000,
        gold=700,
        level=8,
        game_time=600,
        champion_name="Caitlyn",
        assigned_position="BOTTOM",
        creep_score=60,
    )

    with patch.dict("backend.main.CONFIG", {"riot_api_key": "riot-key", "riot_region": "KR", "riot_benchmark_tier": "DIAMOND"}):
        snippet = asyncio.run(_fetch_riot_cs_snippet(state))

    assert snippet is not None
    assert snippet.source == "riot_cs_benchmark:Caitlyn:BOTTOM:DIAMOND"
    assert "60 CS at 10.0m" in snippet.content
    assert "-20%" in snippet.content


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
