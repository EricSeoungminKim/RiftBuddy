# backend/timeline/detectors/death_streak.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent, Severity


class DeathStreakDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        if state.deaths < 3:
            return []
        severity = Severity.HIGH if state.deaths >= 5 else Severity.MEDIUM
        return [DetectedEvent(
            event_type="DEATH_STREAK",
            severity=severity,
            reason=f"{state.deaths}데스 — 안전 플레이 필요",
            recommended_action="교전 회피, 팜 위주로 플레이, 상대 실수 기다리기",
        )]
