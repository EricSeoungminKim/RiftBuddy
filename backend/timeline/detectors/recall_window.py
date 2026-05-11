# backend/timeline/detectors/recall_window.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent


class RecallWindowDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        return []  # TODO: detect safe recall windows based on wave state
