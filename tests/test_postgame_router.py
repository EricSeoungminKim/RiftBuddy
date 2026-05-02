from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from backend.postgame.router import router, game_session
from backend.riot.live_client import GameState

test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)

_SNAPSHOT_PAYLOAD = {
    "current_health": 1500.0,
    "max_health": 2000.0,
    "gold": 3000.0,
    "level": 9,
    "game_time": 300.0,
    "champion_name": "Rumble",
    "kills": 2,
    "deaths": 1,
    "assists": 3,
    "creep_score": 80,
}

_MOCK_LLM_RESPONSE = (
    "[잘한 점]\n초반 CS를 잘 챙겼습니다.\n"
    "[개선할 점]\n시야 점수를 높이세요.\n"
    "[주요 순간]\n5분에 첫 킬.\n"
    "[다음 게임 목표]\n와드를 더 박으세요."
)


def _seed_session():
    game_session.clear()
    state = GameState(
        current_health=1500,
        max_health=2000,
        gold=3000,
        level=9,
        game_time=300.0,
        champion_name="Rumble",
        kills=2,
        deaths=1,
        assists=3,
        creep_score=80,
    )
    game_session.add_snapshot(state)


def test_delete_snapshots_returns_cleared():
    game_session.clear()
    resp = client.delete("/game/snapshots")
    assert resp.status_code == 200
    assert resp.json() == {"cleared": True}


def test_coach_empty_session_returns_400():
    game_session.clear()
    resp = client.post("/postgame/coach")
    assert resp.status_code == 400


def test_coach_returns_parsed_sections():
    _seed_session()
    with patch("backend.postgame.router.get_advice", new=AsyncMock(return_value=_MOCK_LLM_RESPONSE)):
        resp = client.post("/postgame/coach")
    assert resp.status_code == 200
    data = resp.json()
    assert "strengths" in data
    assert "improvements" in data
    assert "moments" in data
    assert "goals" in data
    assert "CS" in data["strengths"]
    assert "시야" in data["improvements"]
