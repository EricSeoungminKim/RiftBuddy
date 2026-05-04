import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.context.engine import ContextPacket
from backend.draft.opgg_client import get_champion_analysis, get_matchup, get_meta_champions, get_runes
from backend.llm.advisor import get_advice

router = APIRouter()

DEFAULT_META_BY_POSITION = {
    "top": ["Ambessa", "Aatrox", "Garen", "Camille", "Renekton"],
    "jungle": ["XinZhao", "LeeSin", "Viego", "JarvanIV", "Nocturne"],
    "mid": ["Ahri", "Galio", "Orianna", "Sylas", "Yone"],
    "adc": ["Caitlyn", "Jinx", "Kaisa", "Ezreal", "Ashe"],
    "support": ["Nami", "Leona", "Rakan", "Thresh", "Lulu"],
}


@router.get("/draft/champion-analysis")
async def champion_analysis(champion: str, role: str):
    try:
        return await get_champion_analysis(champion, role)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"op.gg MCP error: {exc}")


@router.get("/draft/matchup")
async def matchup(my_champion: str, enemy_champion: str, role: str):
    try:
        data = await get_matchup(my_champion, enemy_champion, role)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"op.gg MCP error: {exc}")
    enriched = _with_matchup_metrics(data)
    if "winRate" not in enriched:
        try:
            analysis = await get_champion_analysis(my_champion, role)
            counter_rate = _extract_counter_list_matchup_win_rate(analysis, enemy_champion)
        except Exception:
            counter_rate = None
        if counter_rate is not None:
            enriched["winRate"] = counter_rate
            enriched["matchupSource"] = "OP.GG champion counter list"
    return enriched


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
    matchups: list[dict] = []


@router.post("/draft/team-strategy")
async def team_strategy(body: TeamStrategyRequest):
    ally_str = ", ".join(body.ally)
    enemy_str = ", ".join(body.enemy)
    prompt = (
        f"Ally comp: {ally_str}. Enemy comp: {enemy_str}. "
        f"My champion: {body.my_champion} ({body.my_role}). "
        f"Enemy matchup win-rate evidence: {_matchup_summary(body.matchups)}. "
        "Do not invent generic strategy. Use only the shown comps and matchup evidence. "
        "Give concise English advice for teamfights, side-lane setup, objective timing, and fights to avoid."
    )
    dummy_packet = ContextPacket(
        health_percent=100.0,
        gold=0.0,
        level=1,
        game_time_minutes=0.0,
        summary=prompt,
    )
    try:
        strategy = await get_advice(dummy_packet, user_query=prompt, language="en")
    except Exception as exc:
        strategy = _fallback_team_strategy(body)
    return {"strategy": strategy}


class RecommendForRoleRequest(BaseModel):
    ally: list[str]
    enemy: list[str]
    my_role: str
    language: str = "en"


@router.post("/draft/recommend-for-role")
async def recommend_for_role(body: RecommendForRoleRequest):
    pos = _normalize_position(body.my_role)
    try:
        meta = await get_meta_champions(pos)
    except Exception as exc:
        meta = _fallback_meta(pos)

    top_meta = meta[:10] if isinstance(meta, list) else []
    meta_names = [_meta_champion_name(c) for c in top_meta]
    meta_names = [name for name in meta_names if name]

    relevant_enemies = await _relevant_enemies_for_position([enemy for enemy in body.enemy if enemy], pos)
    available_meta = _available_recommendation_meta(top_meta, body)
    recommendations = await _recommendations_from_matchups(available_meta, body, pos, relevant_enemies)
    return {"recommendations": recommendations, "meta": meta_names}


@router.get("/draft/ban-counters")
async def ban_counters(role: str, champion: str = ""):
    pos = _normalize_position(role)
    counters: list[dict] = []
    if champion:
        try:
            data = await get_champion_analysis(champion, pos)
            counters.extend(_extract_ban_counters(data, champion))
        except Exception:
            counters = []
    try:
        meta = await get_meta_champions(pos)
    except Exception:
        meta = _fallback_meta(pos)
    counters.extend(_role_meta_bans(meta, champion))
    return {"target": champion, "counters": _unique_champion_rows(counters)[:5]}


def _normalize_position(role: str) -> str:
    from backend.draft.opgg_client import _POSITION_MAP
    return _POSITION_MAP.get(role.lower(), role.lower())


def _fallback_meta(position: str) -> list[dict]:
    names = DEFAULT_META_BY_POSITION.get(position, DEFAULT_META_BY_POSITION["mid"])
    return [{"champion": name} for name in names]


def _parse_recommendations(text: str) -> list[dict]:
    import re
    lines = text.strip().split("\n")
    results = []
    for line in lines:
        m = re.match(r"\d+\.\s*(.+?):\s*(.+)", line.strip())
        if m:
            results.append({"champion": m.group(1).strip(), "reason": m.group(2).strip()})
    return results[:3]


def _meta_champion_name(champion: object) -> str:
    if isinstance(champion, str):
        return champion
    if not isinstance(champion, dict):
        return ""
    for key in ("champion_name", "champion", "name", "id"):
        value = champion.get(key)
        if isinstance(value, str) and value:
            return value
    nested = champion.get("champion")
    if isinstance(nested, dict):
        return _meta_champion_name(nested)
    return ""


def _fallback_recommendations(meta: list, role: str, language: str) -> list[dict]:
    return _recommendations_from_meta(meta, RecommendForRoleRequest(ally=[], enemy=[], my_role=role, language=language))[:3]


def _recommendations_from_meta(meta: list, body: RecommendForRoleRequest) -> list[dict]:
    results = []
    for champion in _available_recommendation_meta(meta, body):
        name = _meta_champion_name(champion)
        if not name:
            continue
        results.append({"champion": name, "reason": _recommendation_reason(name, champion, body)})
    return results[:5]


def _available_recommendation_meta(meta: list, body: RecommendForRoleRequest) -> list:
    unavailable = {champion for champion in body.ally + body.enemy if champion}
    return [champion for champion in meta if _meta_champion_name(champion) not in unavailable]


async def _recommendations_from_matchups(
    meta: list,
    body: RecommendForRoleRequest,
    position: str,
    relevant_enemies: list[str] | None = None,
) -> list[dict]:
    enemies = relevant_enemies if relevant_enemies is not None else [enemy for enemy in body.enemy if enemy]
    if not enemies:
        return _recommendations_from_meta(meta, body)
    scored = await _score_candidates(meta[:12], enemies, position)
    positives = [row for row in scored if row["positiveCount"] > 0]
    positives.sort(key=lambda row: (row["positiveCount"], row["winRate"], row["metaWinRate"]), reverse=True)
    results = [_counter_recommendation(row) for row in positives[:5]]
    if len(results) < 5:
        used = {item["champion"] for item in results}
        results.extend(item for item in _recommendations_from_meta(meta, body) if item["champion"] not in used)
    return results[:5]


async def _relevant_enemies_for_position(enemies: list[str], position: str) -> list[str]:
    if not enemies:
        return []
    relevant_positions = _enemy_relevance_positions(position)
    if not relevant_positions:
        return enemies
    relevant_names: set[str] = set()
    for relevant_position in relevant_positions:
        try:
            meta = await get_meta_champions(relevant_position)
        except Exception:
            meta = _fallback_meta(relevant_position)
        relevant_names.update(_meta_champion_name(champion) for champion in meta)
    filtered = [enemy for enemy in enemies if enemy in relevant_names]
    return filtered or enemies


def _enemy_relevance_positions(position: str) -> list[str]:
    if position == "adc":
        return ["adc", "support"]
    return [position]


async def _score_candidates(meta: list, enemies: list[str], position: str) -> list[dict]:
    semaphore = asyncio.Semaphore(8)

    async def score_candidate(champion: object) -> dict:
        name = _meta_champion_name(champion)
        matchups = await asyncio.gather(*[
            _safe_matchup_score(name, enemy, position, semaphore) for enemy in enemies
        ])
        valid = [item for item in matchups if item["winRate"] is not None]
        positive = [item for item in valid if item["winRate"] > 51.0]
        win_rate = sum(item["winRate"] for item in valid) / len(valid) if valid else None
        return {
            "champion": name,
            "matchups": valid,
            "positiveCount": len(positive),
            "winRate": win_rate or 0.0,
            "metaWinRate": _percent(_find_number(champion, ("win_rate", "winRate", "winning_rate"))) or 0.0,
        }

    return [row for row in await asyncio.gather(*[score_candidate(c) for c in meta]) if row["champion"]]


async def _safe_matchup_score(champion: str, enemy: str, position: str, semaphore: asyncio.Semaphore) -> dict:
    async with semaphore:
        try:
            data = await get_matchup(champion, enemy, position)
            win_rate = _extract_matchup_win_rate(data)
            source = "OP.GG matchup analysis"
        except Exception:
            win_rate = None
            source = ""
        if win_rate is None:
            try:
                analysis = await get_champion_analysis(champion, position)
                win_rate = _extract_counter_list_matchup_win_rate(analysis, enemy)
                source = "OP.GG champion counter list" if win_rate is not None else ""
            except Exception:
                win_rate = None
                source = ""
    return {"enemy": enemy, "winRate": win_rate, "source": source}


def _counter_recommendation(row: dict) -> dict:
    positives = [item for item in row["matchups"] if item["winRate"] and item["winRate"] > 51.0]
    positives.sort(key=lambda item: item["winRate"], reverse=True)
    counter_bits = [f"Counters {item['enemy']} at {item['winRate']:.1f}% from OP.GG" for item in positives[:2]]
    reason = "; ".join(counter_bits)
    return {
        "champion": row["champion"],
        "reason": f"{reason}.",
        "winRate": round(row["winRate"], 1),
        "source": "OP.GG matchup analysis",
        "matchups": row["matchups"],
    }


def _recommendation_reason(name: str, champion: object, body: RecommendForRoleRequest) -> str:
    enemy = next((item for item in body.enemy if item), "")
    ally = next((item for item in body.ally if item and item != name), "")
    win_rate = _percent(_find_number(champion, ("win_rate", "winRate", "winning_rate")))
    win_text = f" at {win_rate:.1f}% role win rate" if win_rate else ""
    if enemy:
        return f"OP.GG role-meta fallback{win_text}; no matchup above 51% was confirmed yet."
    if ally:
        return f"OP.GG role-meta fallback{win_text}; pairs reasonably with ally {ally}."
    return f"OP.GG role-meta fallback{win_text}; safe blind option for this role."


def _fallback_team_strategy(body: TeamStrategyRequest) -> str:
    ally = ", ".join(body.ally[:5]) if body.ally else "아군 픽"
    enemy = ", ".join(body.enemy[:5]) if body.enemy else "상대 픽"
    matchup_text = _matchup_summary(body.matchups)
    return (
        f"With {body.my_champion} ({body.my_role}), your comp ({ally}) should play around vision setup and synchronized first move. "
        f"Against {enemy}, use these matchup notes ({matchup_text}) and avoid starting fights before key crowd control and objective setup are ready."
    )


def _matchup_summary(matchups: list[dict]) -> str:
    parts = []
    for item in matchups[:5]:
        enemy = item.get("enemyChampion") or item.get("enemy")
        win_rate = _coerce_number(item.get("winRate") or item.get("win_rate"))
        if enemy and win_rate is not None:
            parts.append(f"{enemy}전 {win_rate:.1f}%")
    return ", ".join(parts) if parts else "no confirmed matchup win-rate data yet"


def _extract_ban_counters(data: dict, champion: str) -> list[dict]:
    raw_counters = _find_counter_list(data, ("weak_counters", "hard_counters", "counters", "bad_matchups"))
    results = []
    for item in raw_counters:
        name = _meta_champion_name(item)
        if not name:
            continue
        win_rate = _find_number(item, ("win_rate", "winRate", "winning_rate"))
        reason = f"OP.GG lists {name} as a difficult counter into {champion}."
        if win_rate is not None:
            display = _percent(win_rate)
            reason = f"{champion} only wins {display:.1f}% into {name}; ban source is OP.GG counter analysis."
        results.append({"champion": name, "winRate": _percent(win_rate), "reason": reason, "source": "OP.GG counter analysis"})
    return results[:5]


def _extract_counter_list_matchup_win_rate(data: object, enemy_champion: str) -> float | None:
    enemy_key = _champion_key(enemy_champion)
    strong = _find_named_counter(data, ("strong_counters", "good_matchups"), enemy_key)
    if strong is not None:
        return _percent(strong)
    weak = _find_named_counter(data, ("weak_counters", "bad_matchups", "hard_counters"), enemy_key)
    if weak is None:
        return None
    weak_rate = _percent(weak)
    return round(100 - weak_rate, 1) if weak_rate is not None else None


def _find_named_counter(value: object, keys: tuple[str, ...], enemy_key: str) -> float | None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and isinstance(item, list):
                for counter in item:
                    if _champion_key(_meta_champion_name(counter)) != enemy_key:
                        continue
                    win_rate = _find_number(counter, ("win_rate", "winRate", "winning_rate"))
                    if win_rate is not None:
                        return win_rate
            nested = _find_named_counter(item, keys, enemy_key)
            if nested is not None:
                return nested
    if isinstance(value, list):
        for item in value:
            nested = _find_named_counter(item, keys, enemy_key)
            if nested is not None:
                return nested
    return None


def _champion_key(name: str) -> str:
    return name.lower().replace(" ", "").replace("'", "").replace(".", "")


def _role_meta_bans(meta: list, champion: str) -> list[dict]:
    results = []
    for item in meta:
        name = _meta_champion_name(item)
        if not name or name == champion or not _is_priority_meta_pick(item):
            continue
        tier = _tier_label(item)
        win_rate = _percent(_find_number(item, ("win_rate", "winRate", "winning_rate")))
        win_text = f" with {win_rate:.1f}% role win rate" if win_rate else ""
        reason = f"OP.GG marks {name} as {tier}{win_text}; this is a role-meta ban, not matchup analysis."
        results.append({"champion": name, "winRate": win_rate, "reason": reason, "source": "OP.GG role meta"})
    return results


def _find_counter_list(value: object, keys: tuple[str, ...]) -> list:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and isinstance(item, list):
                return item
            nested = _find_counter_list(item, keys)
            if nested:
                return nested
    if isinstance(value, list):
        for item in value:
            nested = _find_counter_list(item, keys)
            if nested:
                return nested
    return []


def _with_matchup_metrics(data: dict) -> dict:
    if not isinstance(data, dict):
        return {"raw": data}
    enriched = dict(data)
    win_rate = _extract_matchup_win_rate(data)
    if win_rate is not None:
        enriched["winRate"] = win_rate
    return enriched


def _extract_matchup_win_rate(data: object) -> float | None:
    for key in ("lane_matchup", "matchup", "matchups", "opponent", "opponent_champion"):
        section = _find_section(data, key)
        win_rate = _find_number(section, ("win_rate", "winRate", "winning_rate", "my_win_rate"))
        if win_rate is not None:
            return _percent(win_rate)
    return _percent(_find_number(data, ("my_win_rate", "matchup_win_rate")))


def _find_number(value: object, keys: tuple[str, ...]) -> float | None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                parsed = _coerce_number(item)
                if parsed is not None:
                    return parsed
            nested = _find_number(item, keys)
            if nested is not None:
                return nested
    if isinstance(value, list):
        for item in value:
            nested = _find_number(item, keys)
            if nested is not None:
                return nested
    return None


def _coerce_number(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace("%", ""))
        except ValueError:
            return None
    return None


def _percent(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 100 if value <= 1 else value


def _find_section(value: object, key_name: str) -> object | None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == key_name:
                return item
            nested = _find_section(item, key_name)
            if nested is not None:
                return nested
    if isinstance(value, list):
        for item in value:
            nested = _find_section(item, key_name)
            if nested is not None:
                return nested
    return None


def _is_priority_meta_pick(champion: object) -> bool:
    tier = str(_tier_label(champion)).lower()
    rank = _find_number(champion, ("rank", "tier_rank"))
    return tier in {"op", "1", "s", "s+"} or rank == 1


def _tier_label(champion: object) -> str:
    if not isinstance(champion, dict):
        return "high priority"
    for key in ("tier", "rank"):
        value = champion.get(key)
        if value is not None:
            return str(value)
    tier_data = champion.get("tier_data")
    if isinstance(tier_data, dict):
        value = tier_data.get("tier") or tier_data.get("rank")
        if value is not None:
            return str(value)
    return "high priority"


def _unique_champion_rows(rows: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for row in rows:
        champion = row.get("champion")
        if not champion or champion in seen:
            continue
        seen.add(champion)
        unique.append(row)
    return unique
