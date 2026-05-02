from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.context.engine import ContextPacket
from backend.draft.opgg_client import get_champion_analysis, get_matchup, get_meta_champions, get_runes
from backend.llm.advisor import get_advice

router = APIRouter()


@router.get("/draft/champion-analysis")
async def champion_analysis(champion: str, role: str):
    try:
        return await get_champion_analysis(champion, role)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"op.gg MCP error: {exc}")


@router.get("/draft/matchup")
async def matchup(my_champion: str, enemy_champion: str, role: str):
    try:
        return await get_matchup(my_champion, enemy_champion, role)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"op.gg MCP error: {exc}")


@router.get("/draft/runes")
async def runes(champion: str, role: str):
    try:
        return await get_runes(champion, role)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"op.gg MCP error: {exc}")


@router.get("/draft/meta-champions")
async def meta_champions(role: str):
    try:
        return await get_meta_champions(role)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"op.gg MCP error: {exc}")


class TeamStrategyRequest(BaseModel):
    ally: list[str]
    enemy: list[str]
    my_champion: str
    my_role: str


@router.post("/draft/team-strategy")
async def team_strategy(body: TeamStrategyRequest):
    ally_str = ", ".join(body.ally)
    enemy_str = ", ".join(body.enemy)
    prompt = (
        f"아군 조합: {ally_str}. 상대 조합: {enemy_str}. "
        f"내 챔피언: {body.my_champion} ({body.my_role}). "
        "이 드래프트의 승리 조건, 초반 우선순위, 핵심 파워 스파이크, 드래프트 유불리를 한국어로 분석해주세요."
    )
    dummy_packet = ContextPacket(
        health_percent=100.0,
        gold=0.0,
        level=1,
        game_time_minutes=0.0,
        summary=prompt,
    )
    try:
        strategy = await get_advice(dummy_packet, user_query=prompt, language="ko")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")
    return {"strategy": strategy}
