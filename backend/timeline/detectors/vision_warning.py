# backend/timeline/detectors/vision_warning.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent, Severity


class VisionWarningDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        # Support/utility handles vision — don't double-warn
        if packet.assigned_position.upper() == "UTILITY":
            return []
        minutes = state.game_time / 60
        if minutes < 10:
            return []
        if state.ward_score < 2:
            severity = Severity.HIGH
        elif minutes >= 20 and state.ward_score < 10:
            severity = Severity.MEDIUM
        elif state.ward_score < 5:
            severity = Severity.MEDIUM
        else:
            return []
        return [DetectedEvent(
            event_type="VISION_WARNING",
            severity=severity,
            reason=f"와드 점수 {state.ward_score:.0f} — 시야 부족",
            recommended_action="컨트롤 와드 구매, 정글 입구 시야 확보",
        )]
