from dataclasses import dataclass

from backend.riot.live_client import GameState


@dataclass(frozen=True)
class ContextPacket:
    health_percent: float
    gold: float
    level: int
    game_time_minutes: float
    summary: str


def build_context_packet(state: GameState) -> ContextPacket:
    health_percent = round((state.current_health / state.max_health) * 100, 1)
    game_time_minutes = round(state.game_time / 60, 1)

    if health_percent < 30:
        health_status = "low health"
    elif health_percent < 60:
        health_status = "moderate health"
    else:
        health_status = "healthy"

    summary = (
        f"{state.summoner_name} is playing {state.champion_name} in {state.game_mode}. "
        f"Status: {health_status} ({health_percent}% HP), level {state.level}, "
        f"{state.gold:g} gold, {state.creep_score} CS, "
        f"KDA {state.kills}/{state.deaths}/{state.assists}, ward score {state.ward_score:g}. "
        f"Summoner spells: {_format_list(state.summoner_spells)}. "
        f"Items: {_format_list(state.items)}. "
        f"Recent events: {_format_list(state.recent_events)}. "
        f"Game time: {game_time_minutes} minutes."
    )
    return ContextPacket(
        health_percent=health_percent,
        gold=state.gold,
        level=state.level,
        game_time_minutes=game_time_minutes,
        summary=summary,
    )


def _format_list(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"
