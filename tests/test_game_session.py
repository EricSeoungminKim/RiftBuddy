import pytest
from backend.game_session import GameSession
from backend.riot.live_client import GameState


def _make_state(game_time: float = 300.0, kills: int = 2) -> GameState:
    return GameState(
        current_health=1500,
        max_health=2000,
        gold=3000,
        level=9,
        game_time=game_time,
        champion_name="Rumble",
        kills=kills,
        deaths=1,
        assists=3,
        creep_score=80,
    )


def test_add_snapshot_stores_state():
    session = GameSession()
    state = _make_state()
    session.add_snapshot(state)
    assert len(session.snapshots) == 1
    assert session.snapshots[0] is state


def test_add_snapshot_caps_at_60():
    session = GameSession()
    for i in range(65):
        session.add_snapshot(_make_state(game_time=float(i * 30)))
    assert len(session.snapshots) == 60


def test_clear_removes_all():
    session = GameSession()
    session.add_snapshot(_make_state())
    session.add_snapshot(_make_state(game_time=60.0))
    session.clear()
    assert len(session.snapshots) == 0


def test_is_empty_initial():
    session = GameSession()
    assert session.is_empty is True


def test_is_empty_after_add():
    session = GameSession()
    session.add_snapshot(_make_state())
    assert session.is_empty is False


def test_summary_lines_format():
    session = GameSession()
    session.add_snapshot(_make_state(game_time=180.0, kills=2))
    lines = session.summary_lines()
    assert len(lines) == 1
    assert "3:00" in lines[0]
    assert "킬 2" in lines[0]
