from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.context.engine import ContextPacket
from backend.game_session import GameSession
from backend.llm.advisor import get_advice
from backend.riot.live_client import GameState

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


@router.post("/game/snapshot", status_code=201)
async def add_snapshot(payload: SnapshotPayload):
    data = payload.model_dump()
    # Convert lists to tuples for frozen GameState dataclass
    for key in ("ally_champions", "enemy_champions", "all_champions", "items", "summoner_spells", "recent_events"):
        data[key] = tuple(data[key])
    state = GameState(**data)
    game_session.add_snapshot(state)
    return {"stored": len(game_session.snapshots)}


@router.post("/postgame/coach")
async def coach():
    if game_session.is_empty:
        raise HTTPException(status_code=400, detail="No game snapshots recorded.")

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
    return sections


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
