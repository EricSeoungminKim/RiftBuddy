from dataclasses import dataclass

from backend.riot.live_client import GameState

POSITION_LABELS = {
    "TOP": "탑",
    "JUNGLE": "정글",
    "MIDDLE": "미드",
    "MID": "미드",
    "BOTTOM": "바텀",
    "UTILITY": "서폿",
    "SUPPORT": "서폿",
    "NONE": "포지션 미확인",
    "UNKNOWN": "포지션 미확인",
}


@dataclass(frozen=True)
class ContextPacket:
    health_percent: float
    gold: float
    level: int
    game_time_minutes: float
    summary: str
    champion_name: str = "Unknown"
    assigned_position: str = "UNKNOWN"
    creep_score: int = 0


def build_context_packet(state: GameState) -> ContextPacket:
    health_percent = round((state.current_health / state.max_health) * 100, 1)
    game_time_minutes = round(state.game_time / 60, 1)

    if health_percent < 30:
        health_status = "체력 낮음"
    elif health_percent < 60:
        health_status = "체력 보통"
    else:
        health_status = "체력 안정"

    position = normalize_position(state.position)
    assigned_position = normalize_position(state.assigned_position)

    summary = (
        f"소환사 {state.summoner_name}, 챔피언 {state.champion_name}, "
        f"내 배정 포지션 {assigned_position}, 현재 표시 포지션 {position}, 게임 모드 {state.game_mode}. "
        f"상태: {health_status} ({health_percent}% HP), 레벨 {state.level}, "
        f"{state.gold:g}골드, CS {state.creep_score}, "
        f"KDA {state.kills}/{state.deaths}/{state.assists}, 시야 점수 {state.ward_score:g}. "
        f"팀 골드 추정: 아군 {state.ally_gold:g}, 상대 {state.enemy_gold:g}, 차이 {state.gold_diff:g}. "
        f"스펠: {_format_list(state.summoner_spells)}. "
        f"아이템: {_format_list(state.items)}. "
        f"현재 게임 챔피언: {_format_list(state.all_champions)}. "
        f"아군 챔피언: {_format_list(state.ally_champions)}. "
        f"상대 챔피언: {_format_list(state.enemy_champions)}. "
        f"최근 이벤트: {_format_list(state.recent_events)}. "
        f"게임 시간: {game_time_minutes}분."
    )
    return ContextPacket(
        health_percent=health_percent,
        gold=state.gold,
        level=state.level,
        game_time_minutes=game_time_minutes,
        summary=summary,
        champion_name=state.champion_name,
        assigned_position=state.assigned_position,
        creep_score=state.creep_score,
    )


def _format_list(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"


def normalize_position(position: str) -> str:
    return POSITION_LABELS.get(position.upper(), position)


from backend.timeline.schemas import DetectedEvent


def enrich_summary_with_events(packet: ContextPacket, events: list[DetectedEvent]) -> ContextPacket:
    if not events:
        return packet
    lines = ["[DETECTED EVENTS]"]
    for event in events:
        lines.append(f"- {event.event_type} ({event.severity.name}): {event.reason} → {event.recommended_action}")
    event_block = "\n".join(lines)
    return ContextPacket(
        health_percent=packet.health_percent,
        gold=packet.gold,
        level=packet.level,
        game_time_minutes=packet.game_time_minutes,
        summary=f"{event_block}\n\n{packet.summary}",
        champion_name=packet.champion_name,
        assigned_position=packet.assigned_position,
        creep_score=packet.creep_score,
    )
