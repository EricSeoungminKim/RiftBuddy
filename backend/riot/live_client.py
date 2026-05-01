from dataclasses import dataclass, field
import logging
from typing import Optional

import httpx

from backend.config import CONFIG

LIVE_CLIENT_URL = "https://127.0.0.1:2999/liveclientdata"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GameState:
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
    items: tuple[str, ...] = field(default_factory=tuple)
    summoner_spells: tuple[str, ...] = field(default_factory=tuple)
    recent_events: tuple[str, ...] = field(default_factory=tuple)


def get_fake_game_state() -> GameState:
    return GameState(
        current_health=1450,
        max_health=2000,
        gold=2750,
        level=9,
        game_time=720.0,
        champion_name="Rumble",
        summoner_name="LEGENO#2026",
        game_mode="PRACTICETOOL",
        kills=0,
        deaths=0,
        assists=0,
        creep_score=72,
        ward_score=4.0,
        items=("Doran's Shield", "Boots"),
        summoner_spells=("Flash", "Ignite"),
        recent_events=("MinionsSpawning at 0.5m",),
    )


async def _get(path: str) -> dict:
    async with httpx.AsyncClient(verify=False, timeout=2.0, trust_env=False) as client:
        response = await client.get(f"{LIVE_CLIENT_URL}{path}")
        response.raise_for_status()
        return response.json()


async def fetch_game_state() -> Optional[GameState]:
    if CONFIG["test_mode"] == "1":
        return get_fake_game_state()

    try:
        data = await _get("/allgamedata")
        player = data["activePlayer"]
        stats = player["championStats"]
        active_player = _find_active_player(data)
        return GameState(
            current_health=stats["currentHealth"],
            max_health=stats["maxHealth"],
            gold=player["currentGold"],
            level=player["level"],
            game_time=data["gameData"]["gameTime"],
            champion_name=active_player.get("championName", "Unknown"),
            summoner_name=player.get("riotId") or player.get("summonerName", "Unknown"),
            game_mode=data.get("gameData", {}).get("gameMode", "Unknown"),
            kills=active_player.get("scores", {}).get("kills", 0),
            deaths=active_player.get("scores", {}).get("deaths", 0),
            assists=active_player.get("scores", {}).get("assists", 0),
            creep_score=active_player.get("scores", {}).get("creepScore", 0),
            ward_score=active_player.get("scores", {}).get("wardScore", 0.0),
            items=_extract_item_names(active_player),
            summoner_spells=_extract_summoner_spells(active_player),
            recent_events=_extract_recent_events(data),
        )
    except Exception as exc:
        logger.warning("Riot Live Client API unavailable: %s", exc)
        return None


def _find_active_player(data: dict) -> dict:
    active_name = data.get("activePlayer", {}).get("riotId")
    active_summoner = data.get("activePlayer", {}).get("summonerName")
    for player in data.get("allPlayers", []):
        if player.get("riotId") == active_name or player.get("summonerName") == active_summoner:
            return player
    return {}


def _extract_item_names(player: dict) -> tuple[str, ...]:
    names = [
        item.get("displayName") or item.get("rawDisplayName")
        for item in player.get("items", [])
        if item.get("displayName") or item.get("rawDisplayName")
    ]
    return tuple(names)


def _extract_summoner_spells(player: dict) -> tuple[str, ...]:
    spells = player.get("summonerSpells", {})
    names = [
        spell.get("displayName") or spell.get("rawDisplayName")
        for spell in spells.values()
        if spell.get("displayName") or spell.get("rawDisplayName")
    ]
    return tuple(names)


def _extract_recent_events(data: dict) -> tuple[str, ...]:
    events = data.get("events", {}).get("Events", [])[-5:]
    names = [
        f"{event.get('EventName', 'Unknown')} at {round(event.get('EventTime', 0) / 60, 1)}m"
        for event in events
    ]
    return tuple(names)
