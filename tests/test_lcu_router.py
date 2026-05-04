import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from httpx import AsyncClient, Response
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend.lcu.router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

VALID_RUNE_PAGE = {
    "name": "Test Runes",
    "primaryStyleId": 8000,
    "subStyleId": 8100,
    "selectedPerkIds": [8005, 8008, 8014, 8017, 8299, 8304, 5005, 5008, 5002],
}


def _mock_lockfile(tmp_path, port="52123", password="secret"):
    lockfile = tmp_path / "lockfile"
    lockfile.write_text(f"LeagueClient:1234:{port}:{password}:https")
    return lockfile


@patch("backend.lcu.router._LOCKFILE_PATHS", {"darwin": None, "win32": None})
def test_apply_runes_no_lockfile():
    resp = client.post("/lcu/apply-runes", json=VALID_RUNE_PAGE)
    assert resp.status_code == 503


def test_apply_runes_success(tmp_path):
    lockfile = _mock_lockfile(tmp_path)

    current_page_resp = Response(200, json={"id": 42, "name": "Old"})
    delete_resp = Response(204, content=b"")
    create_resp = Response(201, json={"id": 99, "name": "Test Runes"})

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=current_page_resp)
    mock_client.delete = AsyncMock(return_value=delete_resp)
    mock_client.post = AsyncMock(return_value=create_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    import sys
    os_key = "darwin" if sys.platform == "darwin" else "win32"
    patch_paths = {"darwin": lockfile, "win32": lockfile}

    with patch("backend.lcu.router._LOCKFILE_PATHS", patch_paths), \
         patch("backend.lcu.router._make_lcu_client", return_value=mock_client):
        resp = client.post("/lcu/apply-runes", json=VALID_RUNE_PAGE)

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "Test Runes" in data["message"]


def test_apply_runes_missing_fields():
    resp = client.post("/lcu/apply-runes", json={"name": "Incomplete"})
    assert resp.status_code == 422


def test_apply_runes_lcu_unreachable(tmp_path):
    lockfile = _mock_lockfile(tmp_path)
    patch_paths = {"darwin": lockfile, "win32": lockfile}

    error_resp = Response(404, json={"message": "not found"})
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=error_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("backend.lcu.router._LOCKFILE_PATHS", patch_paths), \
         patch("backend.lcu.router._make_lcu_client", return_value=mock_client):
        resp = client.post("/lcu/apply-runes", json=VALID_RUNE_PAGE)

    assert resp.status_code == 502


def test_champ_select_returns_cell_aware_slots(tmp_path):
    lockfile = _mock_lockfile(tmp_path)
    patch_paths = {"darwin": lockfile, "win32": lockfile}
    session = {
        "localPlayerCellId": 1,
        "myTeam": [
            {"cellId": 0, "assignedPosition": "top"},
            {"cellId": 1, "assignedPosition": "jungle"},
        ],
        "theirTeam": [
            {"cellId": 5, "assignedPosition": "top"},
            {"cellId": 6, "assignedPosition": "jungle"},
        ],
        "actions": [
            [
                {"type": "pick", "actorCellId": 1, "championId": 76, "completed": True},
                {"type": "pick", "actorCellId": 5, "championId": 122, "completed": True},
                {"type": "pick", "actorCellId": 6, "championId": 64, "completed": False},
            ]
        ],
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=Response(200, json=session))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("backend.lcu.router._LOCKFILE_PATHS", patch_paths), \
         patch("backend.lcu.router._make_lcu_client", return_value=mock_client), \
         patch("backend.lcu.router._get_champion_id_map", new=AsyncMock(return_value={"76": "Nidalee", "122": "Darius", "64": "LeeSin"})):
        resp = client.get("/lcu/champ-select")

    assert resp.status_code == 200
    data = resp.json()
    assert data["myCell"] == 1
    assert data["allySlots"][1]["cellId"] == 1
    assert data["allySlots"][1]["champion"] == "Nidalee"
    assert data["enemySlots"][0]["cellId"] == 5
    assert data["enemySlots"][0]["champion"] == "Darius"
    assert data["enemySlots"][1]["champion"] == "LeeSin"
    assert data["enemySlots"][1]["completed"] is False
    assert data["ally"] == ["Nidalee"]
    assert data["enemy"] == ["Darius"]


@patch("backend.lcu.router._LOCKFILE_PATHS", {"darwin": None, "win32": None})
def test_champ_select_status_returns_quiet_unavailable():
    resp = client.get("/lcu/champ-select/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is False
    assert data["inProgress"] is False
    assert data["reason"] == "league_client_unavailable"


def test_champ_select_status_returns_quiet_not_in_champ_select(tmp_path):
    lockfile = _mock_lockfile(tmp_path)
    patch_paths = {"darwin": lockfile, "win32": lockfile}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=Response(404, json={"message": "not found"}))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("backend.lcu.router._LOCKFILE_PATHS", patch_paths), \
         patch("backend.lcu.router._make_lcu_client", return_value=mock_client):
        resp = client.get("/lcu/champ-select/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is True
    assert data["inProgress"] is False
    assert data["reason"] == "not_in_champ_select"


def test_champ_select_status_returns_quiet_lcu_disconnect(tmp_path):
    lockfile = _mock_lockfile(tmp_path)
    patch_paths = {"darwin": lockfile, "win32": lockfile}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.RemoteProtocolError("Server disconnected"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("backend.lcu.router._LOCKFILE_PATHS", patch_paths), \
         patch("backend.lcu.router._make_lcu_client", return_value=mock_client):
        resp = client.get("/lcu/champ-select/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is False
    assert data["inProgress"] is False
    assert data["reason"] == "league_client_unavailable"
