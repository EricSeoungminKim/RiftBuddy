import pytest

from backend.stats.riot_cs_benchmarks import (
    CsBenchmark,
    collect_cs_benchmark,
    normalize_position,
    participant_cs,
    timeline_cs_at,
)


class FakeRiotClient:
    platform_region = "KR"

    async def get_platform(self, path, params=None):
        if path.startswith("/lol/league-exp"):
            return [{"puuid": "player-puuid"}]
        raise AssertionError(f"unexpected platform path: {path}")

    async def get_regional(self, path, params=None):
        if path.startswith("/lol/match/v5/matches/by-puuid"):
            return ["KR_1", "KR_2"]
        if path == "/lol/match/v5/matches/KR_1":
            return _match("KR_1", "Caitlyn", "BOTTOM", 160, 20, 1800)
        if path == "/lol/match/v5/matches/KR_1/timeline":
            return _timeline(1, {10: 82, 15: 126, 20: 168})
        if path == "/lol/match/v5/matches/KR_2":
            return _match("KR_2", "Caitlyn", "BOTTOM", 140, 10, 1500)
        if path == "/lol/match/v5/matches/KR_2/timeline":
            return _timeline(1, {10: 70, 15: 108, 20: 144})
        raise AssertionError(f"unexpected regional path: {path}")


def _match(match_id, champion, position, minions, jungle_minions, duration):
    return {
        "metadata": {"matchId": match_id},
        "info": {
            "queueId": 420,
            "gameDuration": duration,
            "participants": [
                {
                    "participantId": 1,
                    "championName": champion,
                    "teamPosition": position,
                    "totalMinionsKilled": minions,
                    "neutralMinionsKilled": jungle_minions,
                }
            ],
        },
    }


def _timeline(participant_id, cs_by_minute):
    frames = []
    for minute in range(21):
        cs = cs_by_minute.get(minute, 0)
        frames.append(
            {
                "participantFrames": {
                    str(participant_id): {
                        "minionsKilled": cs,
                        "jungleMinionsKilled": 0,
                    }
                }
            }
        )
    return {"info": {"frames": frames}}


def test_participant_cs_combines_lane_and_jungle_minions():
    assert participant_cs({"totalMinionsKilled": 120, "neutralMinionsKilled": 8}) == 128


def test_timeline_cs_at_extracts_minute_curve():
    timeline = _timeline(3, {10: 76, 15: 118, 20: 160})

    assert timeline_cs_at(timeline, 3) == {"10": 76, "15": 118, "20": 160}


def test_normalize_position_maps_adc_to_bottom():
    assert normalize_position("adc") == "BOTTOM"


@pytest.mark.asyncio
async def test_collect_cs_benchmark_from_match_v5_samples():
    benchmark = await collect_cs_benchmark(
        FakeRiotClient(),
        champion="Caitlyn",
        position="adc",
        target_samples=2,
        matches_per_player=2,
        max_pages_per_division=1,
    )

    assert isinstance(benchmark, CsBenchmark)
    assert benchmark.samples == 2
    assert benchmark.position == "BOTTOM"
    assert benchmark.avg_cspm == 6.0
    assert benchmark.cs_at == {"10": 76.0, "15": 117.0, "20": 156.0}
    assert benchmark.to_average_stats_payload()["data"]["summary"]["average_stats"]["cs_per_min"] == 6.0
