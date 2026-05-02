import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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
