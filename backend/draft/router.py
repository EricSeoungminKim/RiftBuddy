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


class RecommendForRoleRequest(BaseModel):
    ally: list[str]
    enemy: list[str]
    my_role: str
    language: str = "ko"


@router.post("/draft/recommend-for-role")
async def recommend_for_role(body: RecommendForRoleRequest):
    pos = _normalize_position(body.my_role)
    try:
        meta = await get_meta_champions(pos)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"op.gg MCP error: {exc}")

    top_meta = meta[:10] if isinstance(meta, list) else []
    meta_names = [c.get("champion_name") or c.get("name") or str(c) for c in top_meta if c]

    ally_str = ", ".join(body.ally) if body.ally else "없음"
    enemy_str = ", ".join(body.enemy) if body.enemy else "없음"
    meta_str = ", ".join(meta_names) if meta_names else "정보 없음"

    if body.language == "ko":
        prompt = (
            f"현재 {pos} 포지션 메타 티어 챔피언들: {meta_str}\n"
            f"아군 조합: {ally_str}\n"
            f"상대 조합: {enemy_str}\n\n"
            f"위 메타 티어 챔피언들 중에서 아군 조합과 시너지가 좋고 상대 조합을 잘 상대할 수 있는 "
            f"{pos} 챔피언 3개를 추천해줘. "
            "반드시 다음 형식으로 답해줘:\n"
            "1. [챔피언명]: [한 줄 이유]\n"
            "2. [챔피언명]: [한 줄 이유]\n"
            "3. [챔피언명]: [한 줄 이유]"
        )
    else:
        prompt = (
            f"Meta tier {pos} champions: {meta_str}\n"
            f"Ally comp: {ally_str}\n"
            f"Enemy comp: {enemy_str}\n\n"
            f"Recommend 3 {pos} champions from the meta list that synergize with allies and counter enemies. "
            "Format:\n1. [Champion]: [one-line reason]\n2. [Champion]: [one-line reason]\n3. [Champion]: [one-line reason]"
        )

    dummy_packet = ContextPacket(health_percent=100.0, gold=0.0, level=1, game_time_minutes=0.0, summary=prompt)
    try:
        raw_advice = await get_advice(dummy_packet, user_query=prompt, language=body.language)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    recommendations = _parse_recommendations(raw_advice)
    return {"recommendations": recommendations, "meta": meta_names}


def _normalize_position(role: str) -> str:
    from backend.draft.opgg_client import _POSITION_MAP
    return _POSITION_MAP.get(role.lower(), role.lower())


def _parse_recommendations(text: str) -> list[dict]:
    import re
    lines = text.strip().split("\n")
    results = []
    for line in lines:
        m = re.match(r"\d+\.\s*(.+?):\s*(.+)", line.strip())
        if m:
            results.append({"champion": m.group(1).strip(), "reason": m.group(2).strip()})
    return results[:3]
