from unittest.mock import AsyncMock, patch

import pytest

from backend.game_session import GameSession
from backend.postgame.router import _build_metrics, _fetch_postgame_seed_data
from backend.riot.live_client import GameState
from backend.stats.riot_cs_benchmarks import CsBenchmark


@pytest.mark.asyncio
async def test_fetch_postgame_seed_data_prefers_riot_cs_benchmark():
    session = GameSession()
    session.add_snapshot(
        GameState(
            current_health=1000,
            max_health=1000,
            gold=1000,
            level=10,
            game_time=1200,
            champion_name="Caitlyn",
            assigned_position="BOTTOM",
        )
    )
    benchmark = CsBenchmark(
        champion="Caitlyn",
        position="BOTTOM",
        tier="DIAMOND",
        region="KR",
        samples=2,
        avg_cspm=7.8,
        cs_at={"10": 78.0},
    )

    with patch.dict(
        "backend.postgame.router.CONFIG",
        {
            "test_mode": "0",
            "riot_api_key": "riot-key",
            "riot_region": "KR",
            "riot_game_name": "tester",
            "riot_tag_line": "KR1",
            "riot_benchmark_tier": "DIAMOND",
            "riot_benchmark_samples": "2",
            "riot_benchmark_matches_per_player": "1",
            "riot_benchmark_ttl_seconds": "604800",
        },
    ), patch(
        "backend.postgame.router.get_last_match", new=AsyncMock(return_value={"id": "KR_1"})
    ), patch(
        "backend.postgame.router.fetch_cs_benchmark", new=AsyncMock(return_value=benchmark)
    ), patch(
        "backend.postgame.router.get_champion_analysis_for_comparison", new=AsyncMock()
    ) as opgg_avg:
        match, avg_stats, source = await _fetch_postgame_seed_data(session)

    assert match == {"id": "KR_1"}
    assert source == "Riot Match-V5"
    assert avg_stats["data"]["summary"]["average_stats"]["cs_per_min"] == 7.8
    opgg_avg.assert_not_called()


def test_build_metrics_returns_feedback_dashboard_values():
    session = GameSession()
    session.add_snapshot(
        GameState(
            current_health=900,
            max_health=1000,
            gold=1000,
            level=8,
            game_time=600,
            champion_name="Caitlyn",
            assigned_position="BOTTOM",
            kills=2,
            deaths=1,
            assists=3,
            creep_score=60,
            gold_diff=300,
        )
    )
    session.seed_doc_id = "perf_caitlyn_1"

    metrics = _build_metrics(
        session,
        {"data": {"summary": {"average_stats": {"cs_per_min": 7.5}}}},
        "Riot Match-V5",
    )

    assert metrics.champion == "Caitlyn"
    assert metrics.finalCs == 60
    assert metrics.csPerMinute == 6.0
    assert metrics.csVsAvgPct == 0.8
    assert metrics.seedSaved is True
    assert metrics.seedDocId == "perf_caitlyn_1"
    assert 0 <= metrics.score <= 100
