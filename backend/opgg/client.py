"""OP.GG MCP HTTP client for live champion and matchup data."""
from __future__ import annotations

import asyncio
import json
import httpx

_MCP_URL = "https://mcp-api.op.gg/mcp"
_TIMEOUT = 5.0

_POSITION_MAP = {
    "TOP": "top",
    "JUNGLE": "jungle",
    "MIDDLE": "mid",
    "BOTTOM": "adc",
    "UTILITY": "support",
}


def _to_opgg_name(champion: str) -> str:
    return champion.upper().replace(" ", "_").replace("'", "")


def _to_opgg_position(position: str) -> str:
    return _POSITION_MAP.get(position.upper(), "top")


async def _call(tool: str, arguments: dict) -> dict | None:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(_MCP_URL, json=payload)
        resp.raise_for_status()
    result = resp.json().get("result", {})
    content = result.get("content", [])
    if not content:
        return None
    return json.loads(content[0]["text"])


async def _get_champion_position_rates(champion: str) -> dict[str, float]:
    """Returns {position: role_rate} for a champion across all positions."""
    data = await _call("lol_get_champion_analysis", {
        "game_mode": "ranked",
        "champion": _to_opgg_name(champion),
        "position": "all",
        "desired_output_fields": [
            "data.summary.positions[].name",
            "data.summary.positions[].stats.role_rate",
        ],
    })
    if not data:
        return {}
    rates: dict[str, float] = {}
    for pos in data.get("data", {}).get("summary", {}).get("positions", []):
        name = pos.get("name", "").upper()
        rate = pos.get("stats", {}).get("role_rate", 0.0)
        if name and rate:
            rates[name] = rate
    return rates


async def infer_lane_opponent(
    enemy_champions: list[str],
    my_position: str,
    ambiguity_threshold: float = 0.05,
) -> str | None:
    """
    Infer the most likely lane opponent using OP.GG role_rate data.

    Returns None (fallback) when:
    - No champion clearly dominates my_position
    - Top two candidates are within ambiguity_threshold of each other
    """
    opgg_position = _to_opgg_position(my_position).upper()

    # Fetch role rates for all enemies in parallel
    results = await asyncio.gather(
        *[_get_champion_position_rates(champ) for champ in enemy_champions],
        return_exceptions=True,
    )

    candidates: list[tuple[str, float]] = []
    for champ, result in zip(enemy_champions, results):
        if isinstance(result, Exception) or not result:
            continue
        rate = result.get(opgg_position, 0.0)
        if rate > 0:
            candidates.append((champ, rate))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[1], reverse=True)
    best_champ, best_rate = candidates[0]

    # Ambiguous: two champions within threshold of each other
    if len(candidates) >= 2:
        second_rate = candidates[1][1]
        if abs(best_rate - second_rate) <= ambiguity_threshold:
            return None

    # Also skip if best candidate has low confidence (<30%) in this position
    if best_rate < 0.30:
        return None

    return best_champ


async def get_last_match(
    game_name: str,
    tag_line: str,
    region: str = "KR",
    lang: str = "ko_KR",
) -> dict | None:
    """Fetch the most recent ranked match for a summoner."""
    data = await _call("lol_list_summoner_matches", {
        "game_name": game_name,
        "tag_line": tag_line,
        "region": region,
        "lang": lang,
        "limit": 1,
        "desired_output_fields": [
            "data.game_history[].{id,created_at,game_length_second,game_type}",
            "data.game_history[].average_tier_info.{tier,division}",
            "data.game_history[].participants[].{champion_name,position,team_key}",
            "data.game_history[].participants[].summoner.{game_name,tagline}",
            "data.game_history[].participants[].stats.{op_score,op_score_rank,result,kill,death,assist,minion_kill,total_damage_dealt_to_champions,vision_wards_bought_in_game}",
            "data.game_history[].participants[].stats.op_score_timeline[]",
            "data.game_history[].participants[].items_names[]",
        ],
    })
    if not data:
        return None
    history = data.get("data", {}).get("game_history", [])
    return history[0] if history else None


async def get_champion_analysis_for_comparison(
    champion: str,
    position: str,
) -> dict | None:
    """Fetch Diamond-tier average stats for performance comparison."""
    return await _call("lol_get_champion_analysis", {
        "game_mode": "ranked",
        "champion": _to_opgg_name(champion),
        "position": _to_opgg_position(position),
        "desired_output_fields": [
            "data.summary.average_stats",
            "data.summary.positions[].stats",
        ],
    })


async def get_matchup_guide(
    my_champion: str,
    opponent_champion: str,
    position: str,
    lang: str = "ko_KR",
) -> dict | None:
    return await _call("lol_get_lane_matchup_guide", {
        "my_champion": _to_opgg_name(my_champion),
        "opponent_champion": _to_opgg_name(opponent_champion),
        "position": _to_opgg_position(position),
        "lang": lang,
    })


async def get_champion_counters(
    champion: str,
    position: str,
    lang: str = "ko_KR",
) -> dict | None:
    return await _call("lol_get_champion_analysis", {
        "game_mode": "ranked",
        "champion": _to_opgg_name(champion),
        "position": _to_opgg_position(position),
        "lang": lang,
        "desired_output_fields": [
            "data.strong_counters[].{champion_name,win_rate,play}",
            "data.weak_counters[].{champion_name,win_rate,play}",
            "data.summary.average_stats.{win_rate,tier,rank}",
        ],
    })
