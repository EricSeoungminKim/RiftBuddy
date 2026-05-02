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


async def get_champion_analysis(champion: str, role: str) -> dict:
    key = f"champion_analysis:{champion}:{role}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    result = await _call_opgg_mcp("lol_get_champion_analysis", {"champion_name": champion, "position": role})
    _cache_set(key, result)
    return result


async def get_matchup(my_champion: str, enemy_champion: str, role: str) -> dict:
    key = f"matchup:{my_champion}:{enemy_champion}:{role}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    result = await _call_opgg_mcp("lol_get_lane_matchup_guide", {"champion_name": my_champion, "enemy_champion_name": enemy_champion, "position": role})
    _cache_set(key, result)
    return result


async def get_runes(champion: str, role: str) -> dict:
    key = f"runes:{champion}:{role}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    data = await get_champion_analysis(champion, role)
    runes = data.get("recommended_runes", data.get("runes", data))
    _cache_set(key, runes)
    return runes


async def get_meta_champions(role: str) -> list:
    key = f"meta:{role}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    result = await _call_opgg_mcp("lol_list_lane_meta_champions", {"position": role})
    champions = result if isinstance(result, list) else result.get("champions", [])
    _cache_set(key, champions)
    return champions
