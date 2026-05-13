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
    position: str = "UNKNOWN"
    assigned_position: str = "UNKNOWN"
    ally_champions: tuple[str, ...] = field(default_factory=tuple)
    enemy_champions: tuple[str, ...] = field(default_factory=tuple)
    all_champions: tuple[str, ...] = field(default_factory=tuple)
    ally_gold: float = 0.0
    enemy_gold: float = 0.0
    gold_diff: float = 0.0
    items: tuple[str, ...] = field(default_factory=tuple)
    summoner_spells: tuple[str, ...] = field(default_factory=tuple)
    recent_events: tuple[str, ...] = field(default_factory=tuple)
    lane_opponent: str | None = None
    fed_enemy: str | None = None


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
        position="TOP",
        assigned_position="TOP",
        ally_champions=("럼블",),
        enemy_champions=("트린다미어", "갈리오", "다리우스", "브라움", "트리스타나"),
        all_champions=("럼블", "트린다미어", "갈리오", "다리우스", "브라움", "트리스타나"),
        ally_gold=12500,
        enemy_gold=11000,
        gold_diff=1500,
        items=("Doran's Shield", "Boots"),
        summoner_spells=("Flash", "Ignite"),
        recent_events=("MinionsSpawning at 0.5m",),
        lane_opponent="Tryndamere",
        fed_enemy="Darius",
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
        if not active_player:
            logger.warning(
                "Could not match activePlayer (riotId=%r summonerName=%r) in allPlayers — CS/KDA will be 0",
                data.get("activePlayer", {}).get("riotId"),
                data.get("activePlayer", {}).get("summonerName"),
            )
        champion_groups = _extract_champion_groups(data, active_player)
        gold_totals = _estimate_team_gold(data, active_player)
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
            position=active_player.get("position", "UNKNOWN"),
            assigned_position=active_player.get("position", "UNKNOWN"),
            ally_champions=champion_groups["ally_champions"],
            enemy_champions=champion_groups["enemy_champions"],
            all_champions=champion_groups["all_champions"],
            ally_gold=gold_totals["ally_gold"],
            enemy_gold=gold_totals["enemy_gold"],
            gold_diff=gold_totals["gold_diff"],
            items=_extract_item_names(active_player),
            summoner_spells=_extract_summoner_spells(active_player),
            recent_events=_extract_recent_events(data),
            lane_opponent=_infer_lane_opponent(data, active_player),
            fed_enemy=_infer_fed_enemy(data, active_player),
        )
    except Exception as exc:
        logger.warning("Riot Live Client API unavailable: %s", exc)
        return None


def _find_active_player(data: dict) -> dict:
    active_name = (data.get("activePlayer", {}).get("riotId") or "").strip().lower()
    active_summoner = (data.get("activePlayer", {}).get("summonerName") or "").strip().lower()
    for player in data.get("allPlayers", []):
        p_riot = (player.get("riotId") or "").strip().lower()
        p_summoner = (player.get("summonerName") or "").strip().lower()
        if (active_name and p_riot == active_name) or (active_summoner and p_summoner == active_summoner):
            return player
    return {}


def _infer_lane_opponent(data: dict, active_player: dict) -> str | None:
    active_team = active_player.get("team")
    active_position = active_player.get("position", "").upper()
    if not active_team or not active_position:
        return None
    for player in data.get("allPlayers", []):
        if player.get("team") == active_team:
            continue
        if player.get("position", "").upper() == active_position:
            return player.get("championName")
    return None


def _infer_fed_enemy(data: dict, active_player: dict) -> str | None:
    active_team = active_player.get("team")
    best_name: str | None = None
    best_kills = 0
    for player in data.get("allPlayers", []):
        if player.get("team") == active_team:
            continue
        kills = player.get("scores", {}).get("kills", 0) or 0
        if kills > best_kills:
            best_kills = kills
            best_name = player.get("championName")
    return best_name if best_kills > 0 else None


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


def _extract_champion_groups(data: dict, active_player: dict) -> dict[str, tuple[str, ...]]:
    active_team = active_player.get("team")
    allies: list[str] = []
    enemies: list[str] = []
    all_champions: list[str] = []

    for player in data.get("allPlayers", []):
        champion_name = player.get("championName")
        if not champion_name:
            continue
        all_champions.append(champion_name)
        if active_team and player.get("team") == active_team:
            allies.append(champion_name)
        elif active_team:
            enemies.append(champion_name)

    return {
        "ally_champions": tuple(allies),
        "enemy_champions": tuple(enemies),
        "all_champions": tuple(all_champions),
    }


def _estimate_team_gold(data: dict, active_player: dict) -> dict[str, float]:
    active_team = active_player.get("team")
    ally_gold = 0.0
    enemy_gold = 0.0

    for player in data.get("allPlayers", []):
        total_gold = _estimate_player_gold(player)
        if active_team and player.get("team") == active_team:
            ally_gold += total_gold
        elif active_team:
            enemy_gold += total_gold

    return {
        "ally_gold": ally_gold,
        "enemy_gold": enemy_gold,
        "gold_diff": ally_gold - enemy_gold,
    }


def _estimate_player_gold(player: dict) -> float:
    item_gold = sum(float(item.get("price", 0) or item.get("itemGold", 0) or 0) for item in player.get("items", []))
    scores = player.get("scores", {})
    combat_gold = (
        float(scores.get("kills", 0) or 0) * 300
        + float(scores.get("assists", 0) or 0) * 150
        + float(scores.get("creepScore", 0) or 0) * 20
    )
    return item_gold + combat_gold
