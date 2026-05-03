"""Integration smoke test: draft endpoints wired into the FastAPI app."""
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch


def _stub_module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for key, val in attrs.items():
        setattr(mod, key, val)
    return mod


# ---------------------------------------------------------------------------
# Stub optional native / cloud packages that are not installed in CI.
# Must happen before any backend.* import resolves these names.
# ---------------------------------------------------------------------------

if "supabase" not in sys.modules:
    _supabase_stub = _stub_module("supabase", Client=type("Client", (), {}), create_client=MagicMock())
    sys.modules["supabase"] = _supabase_stub

if "whisper" not in sys.modules:
    _whisper_stub = _stub_module("whisper", Whisper=type("Whisper", (), {}), load_model=MagicMock())
    sys.modules["whisper"] = _whisper_stub

if "numpy" not in sys.modules:
    import importlib
    try:
        importlib.import_module("numpy")
    except ModuleNotFoundError:
        sys.modules["numpy"] = _stub_module("numpy", ndarray=object, float32=float)

if "sounddevice" not in sys.modules:
    sys.modules["sounddevice"] = _stub_module("sounddevice")

if "soundfile" not in sys.modules:
    sys.modules["soundfile"] = _stub_module("soundfile")

if "pvporcupine" not in sys.modules:
    sys.modules["pvporcupine"] = _stub_module("pvporcupine")

if "pyaudio" not in sys.modules:
    sys.modules["pyaudio"] = _stub_module("pyaudio")

if "elevenlabs" not in sys.modules:
    sys.modules["elevenlabs"] = _stub_module("elevenlabs")

# ---------------------------------------------------------------------------
# Now import the real app — all routing is exercised, no mocks for routing.
# ---------------------------------------------------------------------------
from starlette.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


def test_champion_analysis_route_exists():
    """GET /draft/champion-analysis is registered and returns 200 with mock."""
    mock_data = {"winRate": 0.52, "tier": "A", "tips": ["tip1"]}
    # Patch the name as imported into the router module (not the source module).
    with patch("backend.draft.router.get_champion_analysis", new_callable=AsyncMock, return_value=mock_data):
        resp = client.get("/draft/champion-analysis?champion=Ahri&role=mid")
    assert resp.status_code == 200
    assert resp.json()["winRate"] == 0.52


def test_matchup_route_exists():
    """GET /draft/matchup returns 200 with mock."""
    mock_data = {"advantage": "유리", "tips": ["tip"]}
    with patch("backend.draft.router.get_matchup", new_callable=AsyncMock, return_value=mock_data):
        resp = client.get("/draft/matchup?my_champion=Ahri&enemy_champion=Zed&role=mid")
    assert resp.status_code == 200


def test_runes_route_exists():
    """GET /draft/runes returns 200 with mock."""
    mock_data = {"primaryStyleId": 8000, "subStyleId": 8100, "selectedPerkIds": [8005, 8008]}
    with patch("backend.draft.router.get_runes", new_callable=AsyncMock, return_value=mock_data):
        resp = client.get("/draft/runes?champion=Ahri&role=mid")
    assert resp.status_code == 200


def test_team_strategy_route_exists():
    """POST /draft/team-strategy returns 200 with mocked LLM."""
    payload = {
        "ally": ["Ahri", "Vi", "Garen", "Jinx", "Thresh"],
        "enemy": ["Zed"],
        "my_champion": "Ahri",
        "my_role": "mid",
    }
    with patch("backend.draft.router.get_advice", new_callable=AsyncMock, return_value="팀 전략 텍스트"):
        resp = client.post("/draft/team-strategy", json=payload)
    assert resp.status_code == 200
    assert resp.json()["strategy"] == "팀 전략 텍스트"


def test_apply_runes_route_exists():
    """POST /lcu/apply-runes returns 503 when lockfile not found (no League client in CI)."""
    payload = {
        "name": "Test",
        "primaryStyleId": 8000,
        "subStyleId": 8100,
        "selectedPerkIds": [8005, 8008, 8014, 8017, 8299, 8304, 5005, 5008, 5002],
    }
    with patch("backend.lcu.router._LOCKFILE_PATHS", {"darwin": None, "win32": None}):
        resp = client.post("/lcu/apply-runes", json=payload)
    # 503 = lockfile not found (expected in CI), 200 = League client running
    assert resp.status_code == 503
