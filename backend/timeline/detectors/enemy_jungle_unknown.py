# backend/timeline/detectors/enemy_jungle_unknown.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent


class EnemyJungleUnknownDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        return []  # TODO: detect when enemy jungler position is unknown and player is pushed
