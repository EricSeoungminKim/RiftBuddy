import json as _json
import time
from typing import Any

import httpx

OPGG_MCP_URL = "https://mcp-api.op.gg/mcp"
CACHE_TTL_SECONDS = 600

_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    if key not in _cache:
        return None
    ts, value = _cache[key]
    if time.monotonic() - ts > CACHE_TTL_SECONDS:
        del _cache[key]
        return None
    return value


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (time.monotonic(), value)


async def _call_opgg_mcp(tool: str, arguments: dict) -> dict:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(OPGG_MCP_URL, json=payload)
        response.raise_for_status()
        data = response.json()
    result = data.get("result", data)
    if isinstance(result, dict) and "content" in result:
        content = result["content"]
        if isinstance(content, list) and content:
            raw = content[0].get("text", "{}")
            return _json.loads(raw) if isinstance(raw, str) else raw
    return result


_POSITION_MAP = {
    "bottom": "adc",
    "바텀": "adc",
    "top": "top",
    "탑": "top",
    "jungle": "jungle",
    "정글": "jungle",
    "mid": "mid",
    "미드": "mid",
    "support": "support",
    "서폿": "support",
    "adc": "adc",
}

_ANALYSIS_FIELDS = [
    "data.summary.average_stats.{ban_rate,pick_rate,win_rate,tier}",
    "data.summary.average_stats.tier_data.{rank,tier}",
    "data.runes.{primary_page_name,primary_rune_names[],secondary_page_name,secondary_rune_names[],stat_mod_names[]}",
    "data.core_items.{ids_names[],win}",
    "data.skills.{order[],pick_rate,win}",
    "data.strong_counters[].{champion_name,win_rate}",
    "data.weak_counters[].{champion_name,win_rate}",
    "data.{damage_type}",
]


def _normalize_champion(name: str) -> str:
    return name.upper().replace(" ", "_").replace("'", "")


def _normalize_position(role: str) -> str:
    return _POSITION_MAP.get(role.lower(), role.lower())


async def get_champion_analysis(champion: str, role: str) -> dict:
    pos = _normalize_position(role)
    champ = _normalize_champion(champion)
    key = f"champion_analysis:{champ}:{pos}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    result = await _call_opgg_mcp("lol_get_champion_analysis", {
        "champion": champ,
        "position": pos,
        "game_mode": "ranked",
        "desired_output_fields": _ANALYSIS_FIELDS,
    })
    _cache_set(key, result)
    return result


async def get_matchup(my_champion: str, enemy_champion: str, role: str) -> dict:
    pos = _normalize_position(role)
    my_champ = _normalize_champion(my_champion)
    enemy_champ = _normalize_champion(enemy_champion)
    key = f"matchup:{my_champ}:{enemy_champ}:{pos}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    result = await _call_opgg_mcp("lol_get_lane_matchup_guide", {
        "my_champion": my_champ,
        "opponent_champion": enemy_champ,
        "position": pos,
    })
    _cache_set(key, result)
    return result


async def get_runes(champion: str, role: str) -> dict:
    pos = _normalize_position(role)
    champ = _normalize_champion(champion)
    key = f"runes:{champ}:{pos}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    data = await get_champion_analysis(champion, role)
    runes = data.get("data", {}).get("runes", data.get("runes", {}))
    _cache_set(key, runes)
    return runes


async def get_meta_champions(role: str) -> list:
    pos = _normalize_position(role)
    key = f"meta:{pos}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    result = await _call_opgg_mcp("lol_list_lane_meta_champions", {"position": pos})
    champions = result if isinstance(result, list) else result.get("champions", [])
    _cache_set(key, champions)
    return champions
