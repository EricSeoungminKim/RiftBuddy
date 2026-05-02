import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from backend.draft.router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_champion_analysis_returns_200():
    mock_data = {"win_rate": 52.3, "tier": "A"}
    with patch("backend.draft.router.get_champion_analysis", new_callable=AsyncMock, return_value=mock_data):
        res = client.get("/draft/champion-analysis?champion=Rumble&role=TOP")
    assert res.status_code == 200
    assert res.json()["win_rate"] == 52.3


def test_champion_analysis_missing_param_returns_422():
    res = client.get("/draft/champion-analysis?champion=Rumble")
    assert res.status_code == 422


def test_matchup_returns_200():
    mock_data = {"laning_strength": 55.0}
    with patch("backend.draft.router.get_matchup", new_callable=AsyncMock, return_value=mock_data):
        res = client.get("/draft/matchup?my_champion=Rumble&enemy_champion=Darius&role=TOP")
    assert res.status_code == 200
    assert res.json()["laning_strength"] == 55.0


def test_runes_returns_200():
    mock_data = {"primary_path": "Precision", "shards": [5005, 5002, 5001]}
    with patch("backend.draft.router.get_runes", new_callable=AsyncMock, return_value=mock_data):
        res = client.get("/draft/runes?champion=Rumble&role=TOP")
    assert res.status_code == 200
    assert "primary_path" in res.json()


def test_meta_champions_returns_200():
    mock_data = [{"champion": "Darius", "win_rate": 53.0}]
    with patch("backend.draft.router.get_meta_champions", new_callable=AsyncMock, return_value=mock_data):
        res = client.get("/draft/meta-champions?role=TOP")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_team_strategy_returns_strategy():
    mock_advice = "초반 견제를 피하고 6레벨에 교환을 시도하세요."
    with patch("backend.draft.router.get_advice", new_callable=AsyncMock, return_value=mock_advice):
        res = client.post("/draft/team-strategy", json={
            "ally": ["Rumble", "Lee Sin", "Orianna", "Jinx", "Thresh"],
            "enemy": ["Darius", "Vi", "Syndra", "Caitlyn", "Blitzcrank"],
            "my_champion": "Rumble",
            "my_role": "TOP"
        })
    assert res.status_code == 200
    assert "strategy" in res.json()
    assert res.json()["strategy"] == mock_advice
