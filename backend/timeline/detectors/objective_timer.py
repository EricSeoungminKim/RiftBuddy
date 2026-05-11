import re
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent, Severity

_ALERT_WINDOW = 60.0  # seconds before spawn to fire alert

# First spawn times in seconds
_FIRST_SPAWNS = {
    "Dragon": 300.0,
    "Voidgrubs": 480.0,
    "Rift Herald": 900.0,
    "Baron": 1200.0,
}

# Respawn delays in seconds (None = no respawn)
_RESPAWN_DELAYS = {
    "Dragon": 300.0,
    "Baron": 360.0,
}

# Despawn times for one-time objectives
_DESPAWNS = {
    "Voidgrubs": 885.0,   # 14:45
    "Rift Herald": 1185.0, # 19:45
}

# Event name patterns in recent_events strings
_KILL_PATTERNS = {
    "Dragon": r"DragonKill at ([\d.]+)m",
    "Voidgrubs": r"VoidgrubKill at ([\d.]+)m",
    "Rift Herald": r"HeraldKill at ([\d.]+)m",
    "Baron": r"BaronKill at ([\d.]+)m",
}


def _parse_last_kill_minutes(events: tuple[str, ...], pattern: str) -> float | None:
    last = None
    for event in events:
        match = re.search(pattern, event)
        if match:
            last = float(match.group(1))
    return last


class ObjectiveTimerDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        t = state.game_time
        events: list[DetectedEvent] = []

        for obj, first_spawn in _FIRST_SPAWNS.items():
            kill_pattern = _KILL_PATTERNS[obj]
            last_kill_min = _parse_last_kill_minutes(state.recent_events, kill_pattern)
            already_killed = last_kill_min is not None

            # One-time objectives (Voidgrubs, Rift Herald)
            if obj in _DESPAWNS:
                if already_killed:
                    continue
                despawn = _DESPAWNS[obj]
                # Despawn warning: within 60s of despawn and not yet killed
                if despawn - _ALERT_WINDOW <= t < despawn:
                    events.append(DetectedEvent(
                        event_type="OBJECTIVE_SPAWN",
                        severity=Severity.MEDIUM,
                        reason=f"{obj} despawning soon at {despawn/60:.1f}m — not yet secured",
                        recommended_action=f"{obj} 처치 시도 또는 포기 결정",
                    ))
                    continue
                # First spawn alert
                if first_spawn - _ALERT_WINDOW <= t < first_spawn:
                    events.append(DetectedEvent(
                        event_type="OBJECTIVE_SPAWN",
                        severity=Severity.MEDIUM,
                        reason=f"{obj} spawning at {first_spawn/60:.1f}m",
                        recommended_action=f"{obj} 스폰 60초 전 — 합류 여부 판단",
                    ))
                continue

            # Repeating objectives (Dragon, Baron)
            if not already_killed:
                if first_spawn - _ALERT_WINDOW <= t < first_spawn:
                    events.append(DetectedEvent(
                        event_type="OBJECTIVE_SPAWN",
                        severity=Severity.MEDIUM,
                        reason=f"{obj} first spawn at {first_spawn/60:.1f}m",
                        recommended_action=f"{obj} 스폰 60초 전 — 귀환 여부 판단 후 합류",
                    ))
            else:
                respawn_delay = _RESPAWN_DELAYS[obj]
                respawn_time = last_kill_min * 60 + respawn_delay
                if respawn_time - _ALERT_WINDOW <= t < respawn_time:
                    events.append(DetectedEvent(
                        event_type="OBJECTIVE_SPAWN",
                        severity=Severity.MEDIUM,
                        reason=f"{obj} respawning at {respawn_time/60:.1f}m",
                        recommended_action=f"{obj} 리스폰 60초 전 — 귀환 여부 판단 후 합류",
                    ))

        return events
