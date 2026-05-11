# backend/timeline/detectors/gold_spike.py
from backend.context.engine import ContextPacket
from backend.riot.live_client import GameState
from backend.timeline.event_detector import BaseDetector
from backend.timeline.schemas import DetectedEvent, Severity

_HIGH_THRESHOLD = 2500.0
_MEDIUM_THRESHOLD = 1300.0


class GoldSpikeDetector(BaseDetector):
    def detect(self, state: GameState, packet: ContextPacket) -> list[DetectedEvent]:
        if packet.gold >= _HIGH_THRESHOLD:
            return [
                DetectedEvent(
                    event_type="GOLD_SPIKE",
                    severity=Severity.HIGH,
                    reason=f"{packet.gold:.0f} 골드 보유 — 아이템 컴플릿 가능",
                    recommended_action="다음 웨이브 안전하게 정리 후 귀환해서 아이템 구매",
                )
            ]
        if packet.gold >= _MEDIUM_THRESHOLD:
            return [
                DetectedEvent(
                    event_type="GOLD_SPIKE",
                    severity=Severity.MEDIUM,
                    reason=f"{packet.gold:.0f} 골드 보유 — 부분 아이템 구매 가능",
                    recommended_action="귀환 타이밍 고려 — 웨이브 상태와 오브젝트 확인 후 판단",
                )
            ]
        return []
