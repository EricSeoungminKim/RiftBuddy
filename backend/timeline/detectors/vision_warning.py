# backend/timeline/detectors/vision_warning.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent


class VisionWarningDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        return []  # TODO: detect low ward score relative to game time
