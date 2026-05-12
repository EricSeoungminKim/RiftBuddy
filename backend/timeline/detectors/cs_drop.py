# backend/timeline/detectors/cs_drop.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent, Severity

# Diamond avg CS per minute by position
_DIAMOND_CS_PER_MIN: dict[str, float] = {
    "TOP": 7.5,
    "JUNGLE": 5.5,
    "MIDDLE": 8.0,
    "BOTTOM": 8.5,
    "UTILITY": 1.5,
}


class CSDropDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        minutes = state.game_time / 60
        if minutes < 5:  # don't fire in early laning
            return []
        position = packet.assigned_position.upper()
        cs_per_min = _DIAMOND_CS_PER_MIN.get(position)
        if cs_per_min is None:
            return []
        expected_cs = cs_per_min * minutes
        if state.creep_score >= expected_cs * 0.8:
            return []
        deficit = int(expected_cs - state.creep_score)
        severity = Severity.HIGH if state.creep_score < expected_cs * 0.6 else Severity.MEDIUM
        return [DetectedEvent(
            event_type="CS_DROP",
            severity=severity,
            reason=f"CS {state.creep_score} — 다이아 기준 {int(expected_cs)} 예상 (부족: {deficit})",
            recommended_action="웨이브 정리 우선, 교전보다 CS에 집중",
        )]
