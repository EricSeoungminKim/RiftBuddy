from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.schemas import DetectedEvent


class BaseDetector:
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        raise NotImplementedError


class EventDetectorPipeline:
    def __init__(self, detectors: list[BaseDetector]):
        self.detectors = detectors

    def run(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        events: list[DetectedEvent] = []
        for detector in self.detectors:
            events.extend(detector.detect(state, packet))
        return sorted(events, key=lambda e: e.severity.value, reverse=True)
