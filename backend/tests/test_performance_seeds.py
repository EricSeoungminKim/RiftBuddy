"""test_performance_seeds.py

Tests for backend/knowledge/performance_seeds.py (Phase 3.5, Task 2).
"""

import chromadb
import pytest

from backend.game_session import GameSession
from backend.knowledge.performance_seeds import (
    GameSummary,
    generate_seed_text,
    save_game_seed,
    summarize_session,
)
from backend.riot.live_client import GameState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snap(
    champion_name: str,
    kills: int,
    deaths: int,
    assists: int,
    creep_score: int,
    gold_diff: float,
    game_time: float,
) -> GameState:
    return GameState(
        current_health=1000.0,
        max_health=2000.0,
        gold=1000.0,
        level=5,
        game_time=game_time,
        champion_name=champion_name,
        kills=kills,
        deaths=deaths,
        assists=assists,
        creep_score=creep_score,
        gold_diff=gold_diff,
    )


def _three_snap_session() -> GameSession:
    session = GameSession()
    session.add_snapshot(_make_snap("Rumble", 0, 0, 0, 0, 0.0, 0.0))
    session.add_snapshot(_make_snap("Rumble", 2, 1, 1, 60, 300.0, 600.0))
    session.add_snapshot(_make_snap("Rumble", 4, 2, 3, 120, 600.0, 1200.0))
    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_summarize_session_stats():
    session = _three_snap_session()
    summary = summarize_session(session)

    assert summary is not None
    assert summary.champion == "Rumble"
    assert summary.kills == 4
    assert summary.deaths == 2
    assert summary.avg_cs == 60.0
    assert summary.game_duration_minutes == 20.0


def test_summarize_empty_session_returns_none():
    assert summarize_session(GameSession()) is None


def test_generate_seed_text_contains_key_fields():
    summary = GameSummary(
        champion="Rumble",
        kills=4,
        deaths=2,
        assists=3,
        avg_cs=60.0,
        avg_gold_diff=300.0,
        game_duration_minutes=20.0,
        key_moments=[],
    )
    text = generate_seed_text(summary)

    assert "Rumble" in text
    assert "4/2/3" in text
    assert "60" in text
    assert "300" in text


def test_save_game_seed_writes_to_chromadb():
    client = chromadb.EphemeralClient()
    collection = client.get_or_create_collection("test_perf")
    session = _three_snap_session()

    doc_id = save_game_seed(session, collection)

    assert doc_id is not None
    assert isinstance(doc_id, str)
    assert collection.count() == 1


def test_save_game_seed_empty_returns_none():
    client = chromadb.EphemeralClient()
    collection = client.get_or_create_collection("test_perf")

    assert save_game_seed(GameSession(), collection) is None


def test_retrieve_merges_static_and_personal_seeds():
    """retrieve() returns static seeds + personal history seeds combined."""
    client = chromadb.EphemeralClient()

    # Static collection with one Rumble snippet
    static_col = client.get_or_create_collection("static_test")
    static_col.add(
        documents=["Rumble tip: use flamespitter in trades"],
        ids=["static_rumble_1"],
        metadatas=[{"champion": "Rumble", "source": "static"}]
    )

    # Performance collection with one personal seed for Rumble
    perf_col = client.get_or_create_collection("perf_test")
    perf_col.add(
        documents=["Personal history - Rumble: 4/2/3 KDA, avg 60 CS"],
        ids=["perf_rumble_1"],
        metadatas=[{"champion": "Rumble", "source": "performance"}]
    )

    from backend.knowledge.retriever import retrieve
    results = retrieve(
        champion="Rumble",
        lane_opponent=None,
        fed_enemy=None,
        collection=static_col,
        performance_collection=perf_col,
        query="Rumble trading tips",
    )

    assert len(results) >= 2
    sources = [r.source for r in results]
    assert "personal_history" in sources
