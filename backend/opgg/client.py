"""OP.GG MCP HTTP client for live champion and matchup data."""
from __future__ import annotations

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
    import json
    return json.loads(content[0]["text"])


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
