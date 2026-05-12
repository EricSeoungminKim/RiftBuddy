from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import CONFIG
from backend.context.engine import ContextPacket
from backend.game_session import GameSession
from backend.knowledge.performance_seeds import save_game_seed, summarize_session
from backend.llm.advisor import get_advice
from backend.opgg.client import get_last_match, get_champion_analysis_for_comparison
from backend.riot.live_client import GameState
from backend.stats.riot_cs_benchmarks import fetch_cs_benchmark

logger = logging.getLogger(__name__)

router = APIRouter()
game_session = GameSession()

_SECTION_MARKERS = ["[잘한 점]", "[개선할 점]", "[주요 순간]", "[다음 게임 목표]"]
_SECTION_KEYS = ["strengths", "improvements", "moments", "goals"]


class SnapshotPayload(BaseModel):
    current_health: float
    max_health: float
    gold: float
    level: int
    game_time: float
    champion_name: str = "Unknown"
    summoner_name: str = "Unknown"
    game_mode: str = "Unknown"
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    creep_score: int = 0
    ward_score: float = 0.0
    position: str = "UNKNOWN"
    assigned_position: str = "UNKNOWN"
    ally_champions: list[str] = []
    enemy_champions: list[str] = []
    all_champions: list[str] = []
    ally_gold: float = 0.0
    enemy_gold: float = 0.0
    gold_diff: float = 0.0
    items: list[str] = []
    summoner_spells: list[str] = []
    recent_events: list[str] = []


class TimelinePoint(BaseModel):
    minute: float
    cs: int
    goldDiff: float
    healthPercent: float
    kills: int
    deaths: int
    assists: int


class PostGameMetrics(BaseModel):
    champion: str
    position: str
    durationMinutes: float
    kills: int
    deaths: int
    assists: int
    finalCs: int
    csPerMinute: float
    csVsAvgPct: float | None = None
    avgGoldDiff: float
    score: int
    seedSaved: bool
    seedDocId: str | None = None
    benchmarkSource: str


class PostGameCoachResponse(BaseModel):
    strengths: str
    improvements: str
    moments: str
    goals: str
    metrics: PostGameMetrics
    timeline: list[TimelinePoint]
    keyMoments: list[str]


@router.post("/game/snapshot", status_code=201)
async def add_snapshot(payload: SnapshotPayload):
    data = payload.model_dump()
    # Convert lists to tuples for frozen GameState dataclass
    for key in ("ally_champions", "enemy_champions", "all_champions", "items", "summoner_spells", "recent_events"):
        data[key] = tuple(data[key])
    state = GameState(**data)
    game_session.add_snapshot(state)
    return {"stored": len(game_session.snapshots)}


async def _fetch_postgame_seed_data(session: GameSession) -> tuple[dict | None, dict | None, str]:
    """Fetch OP.GG match data and Riot/OP.GG average stats for seed enrichment."""
    game_name = CONFIG.get("riot_game_name", "")
    tag_line = CONFIG.get("riot_tag_line", "")
    region = CONFIG.get("riot_region", "KR")

    snaps = session.snapshots
    champion = snaps[-1].champion_name if snaps else ""
    position = snaps[-1].assigned_position if snaps else ""
    riot_key = CONFIG.get("riot_api_key", "")

    async def _noop() -> None:
        return None

    try:
        opgg_match_coro = (
            get_last_match(game_name, tag_line, region=region)
            if game_name and tag_line
            else _noop()
        )
        riot_benchmark_coro = (
            fetch_cs_benchmark(
                riot_key,
                champion,
                position,
                region=region,
                tier=CONFIG.get("riot_benchmark_tier", "DIAMOND"),
                target_samples=int(CONFIG.get("riot_benchmark_samples", "25")),
                matches_per_player=int(CONFIG.get("riot_benchmark_matches_per_player", "3")),
                ttl_seconds=int(CONFIG.get("riot_benchmark_ttl_seconds", "604800")),
            )
            if riot_key and champion and position
            else _noop()
        )
        match, riot_benchmark = await asyncio.gather(
            opgg_match_coro,
            riot_benchmark_coro,
            return_exceptions=True,
        )
        opgg_match = match if not isinstance(match, Exception) else None
        benchmark = riot_benchmark if not isinstance(riot_benchmark, Exception) else None
        if benchmark:
            return opgg_match, benchmark.to_average_stats_payload(), "Riot Match-V5"

        opgg_avg = (
            await get_champion_analysis_for_comparison(champion, position)
            if champion and position
            else None
        )
        return opgg_match, opgg_avg, "OP.GG MCP"
    except Exception as exc:
        logger.warning("Postgame seed enrichment fetch failed: %s", exc)
        return None, None, "none"


@router.post("/postgame/coach")
async def coach():
    if game_session.is_empty:
        raise HTTPException(status_code=400, detail="No game snapshots recorded.")

    import backend.main as _main
    collection = _main.get_knowledge_collection()
    opgg_match, avg_stats, avg_source = await _fetch_postgame_seed_data(game_session)
    if collection is not None:
        if not game_session.seed_doc_id:
            game_session.seed_doc_id = save_game_seed(
                game_session,
                collection,
                opgg_match=opgg_match,
                opgg_avg_stats=avg_stats,
                avg_stats_source=avg_source,
            )

    lines_text = "\n".join(game_session.summary_lines())
    prompt = f"""다음은 리그 오브 레전드 게임 중 30초 간격으로 기록된 상태 스냅샷입니다:

{lines_text}

위 데이터를 분석해서 타임라인 형식의 코칭 리포트를 한국어로 작성해줘.

각 섹션은 다음 형식을 따라야 해:
- 구체적인 타임스탬프(e.g. 10:35)를 포함한 분석
- "분석: [상황 설명]" → "피드백: [구체적인 개선 방법]" 형식

반드시 다음 네 섹션을 포함해야 합니다:

[잘한 점]
(e.g. "분석: 8:20에 CS 72로 상위 파밍이었음. 피드백: 이 템포를 유지하면 아이템 스파이크가 빨라짐")

[개선할 점]
(e.g. "분석: 10:35에 상대 원딜보다 골드가 1200 낮아졌음. 피드백: 9분에 데스 2개가 직접적인 원인. 피가 없거나 적 정글이 바텀에 보이면 즉시 귀환해.")
(e.g. "분석: 15:20 한타에서 딜링 없이 빠르게 사망. 피드백: 원딜의 핵심은 DPS 유지. 뒤에서 포지션 잡고 안전하게 딜 넣어야 함")

[주요 순간]
(타임스탬프별 중요한 게임 전환점들)

[다음 게임 목표]
(위 분석을 바탕으로 다음 게임에서 집중해야 할 2-3가지 구체적 목표)"""

    dummy_packet = ContextPacket(
        health_percent=100.0,
        gold=0.0,
        level=1,
        game_time_minutes=0.0,
        summary=prompt,
    )
    try:
        raw = await get_advice(dummy_packet, user_query=prompt, language="ko")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    sections = _parse_sections(raw)
    sections = _fill_missing_sections(sections, game_session, avg_stats)
    return PostGameCoachResponse(
        **sections,
        metrics=_build_metrics(game_session, avg_stats, avg_source),
        timeline=_build_timeline(game_session),
        keyMoments=_key_moments(game_session),
    )


@router.delete("/game/snapshots")
async def clear_snapshots():
    game_session.clear()
    return {"cleared": True}


def _parse_sections(text: str) -> dict[str, str]:
    result: dict[str, str] = {key: "" for key in _SECTION_KEYS}
    for i, marker in enumerate(_SECTION_MARKERS):
        start = text.find(marker)
        if start == -1:
            continue
        content_start = start + len(marker)
        # Find next marker boundary
        end = len(text)
        for next_marker in _SECTION_MARKERS[i + 1:]:
            next_pos = text.find(next_marker, content_start)
            if next_pos != -1:
                end = next_pos
                break
        result[_SECTION_KEYS[i]] = text[content_start:end].strip()
    return result


def _fill_missing_sections(
    sections: dict[str, str],
    session: GameSession,
    avg_stats: dict | None,
) -> dict[str, str]:
    metrics = _build_metrics(session, avg_stats, "benchmark")
    cs_delta = None if metrics.csVsAvgPct is None else round((metrics.csVsAvgPct - 1.0) * 100)
    cs_line = (
        "CS benchmark가 없어 절대 CS/min 기준으로만 판단했습니다."
        if cs_delta is None
        else f"CS pace는 기준 대비 {cs_delta:+d}%였습니다."
    )
    if not sections.get("strengths"):
        sections["strengths"] = (
            f"{metrics.champion} {metrics.position}로 {metrics.durationMinutes}분 동안 "
            f"KDA {metrics.kills}/{metrics.deaths}/{metrics.assists}, {metrics.csPerMinute:.1f} CS/min을 기록했습니다. "
            f"평균 골드 차이는 {metrics.avgGoldDiff:+.0f}로, 리드가 있는 구간에서는 tempo를 만들 수 있었습니다."
        )
    if not sections.get("improvements"):
        sections["improvements"] = (
            f"{cs_line} 다음 게임에서는 첫 귀환 전 wave 손실과 사망 직전 위치를 더 엄격하게 관리하세요. "
            "특히 death가 발생한 시간대는 다음 게임 proactive warning의 후보가 됩니다."
        )
    if not sections.get("moments"):
        moments = _key_moments(session)
        sections["moments"] = "\n".join(moments) if moments else "주요 전환점이 충분히 기록되지 않았습니다. 다음 게임에서는 자동 snapshot이 더 쌓이면 timeline 분석이 풍부해집니다."
    if not sections.get("goals"):
        sections["goals"] = (
            "1. 10분 CS 목표를 benchmark 대비 -5% 이내로 유지\n"
            "2. 과거 death window 1분 전에는 wave를 밀기보다 시야와 체력 상태를 먼저 확인\n"
            "3. 골드 리드가 있을 때는 즉시 아이템 전환 후 objective setup으로 연결"
        )
    return sections


def _build_metrics(session: GameSession, avg_stats: dict | None, benchmark_source: str) -> PostGameMetrics:
    summary = summarize_session(session)
    if summary is None:
        raise HTTPException(status_code=400, detail="No game snapshots recorded.")
    last = session.snapshots[-1]
    duration = max(last.game_time / 60, 0.1)
    final_cs = int(last.creep_score)
    cspm = round(final_cs / duration, 2)
    cs_vs = _cs_vs_average(final_cs, duration, avg_stats)
    score = _performance_score(last.kills, last.deaths, last.assists, cspm, cs_vs, summary.avg_gold_diff)
    return PostGameMetrics(
        champion=last.champion_name,
        position=last.assigned_position,
        durationMinutes=round(duration, 1),
        kills=last.kills,
        deaths=last.deaths,
        assists=last.assists,
        finalCs=final_cs,
        csPerMinute=cspm,
        csVsAvgPct=cs_vs,
        avgGoldDiff=summary.avg_gold_diff,
        score=score,
        seedSaved=bool(session.seed_doc_id),
        seedDocId=session.seed_doc_id,
        benchmarkSource=benchmark_source,
    )


def _build_timeline(session: GameSession) -> list[TimelinePoint]:
    points: list[TimelinePoint] = []
    for snap in session.snapshots:
        hp_pct = round((snap.current_health / snap.max_health) * 100, 1) if snap.max_health else 0.0
        points.append(
            TimelinePoint(
                minute=round(snap.game_time / 60, 1),
                cs=snap.creep_score,
                goldDiff=round(snap.gold_diff, 1),
                healthPercent=hp_pct,
                kills=snap.kills,
                deaths=snap.deaths,
                assists=snap.assists,
            )
        )
    return points


def _key_moments(session: GameSession) -> list[str]:
    summary = summarize_session(session)
    return summary.key_moments if summary else []


def _cs_vs_average(final_cs: int, duration_minutes: float, avg_stats: dict | None) -> float | None:
    avg_data = (
        (avg_stats or {})
        .get("data", {})
        .get("summary", {})
        .get("average_stats", {})
    )
    avg_cspm = _positive_number(avg_data.get("cs_per_min") or avg_data.get("cspm"))
    if avg_cspm:
        return round((final_cs / duration_minutes) / avg_cspm, 3)
    avg_cs = _positive_number(avg_data.get("minion_kill_per_game") or avg_data.get("cs") or avg_data.get("avg_cs"))
    if avg_cs:
        return round(final_cs / avg_cs, 3)
    return None


def _positive_number(value: object) -> float | None:
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    if isinstance(value, str):
        try:
            parsed = float(value.replace("%", ""))
        except ValueError:
            return None
        return parsed if parsed > 0 else None
    return None


def _performance_score(
    kills: int,
    deaths: int,
    assists: int,
    cspm: float,
    cs_vs_average: float | None,
    avg_gold_diff: float,
) -> int:
    kda_ratio = (kills + assists) / max(1, deaths)
    kda_component = min(20, kda_ratio * 4)
    if cs_vs_average is not None:
        cs_component = max(-15, min(18, (cs_vs_average - 1.0) * 45))
    else:
        cs_component = max(-12, min(15, (cspm - 5.5) * 4))
    gold_component = max(-15, min(15, avg_gold_diff / 120))
    death_penalty = min(18, deaths * 3)
    return int(max(0, min(100, round(55 + kda_component + cs_component + gold_component - death_penalty))))
