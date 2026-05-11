# backend/timeline/detectors/low_health.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent, Severity

_THRESHOLD = 30.0


class LowHealthDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        if packet.health_percent >= _THRESHOLD:
            return []
        return [
            DetectedEvent(
                event_type="LOW_HEALTH",
                severity=Severity.HIGH,
                reason=f"Health is {packet.health_percent:.0f}% — below safe threshold",
                recommended_action="귀환 또는 교전 회피 — 즉시 안전한 위치로 이동",
            )
        ]
