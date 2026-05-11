from backend.timeline.schemas import DetectedEvent, Severity
from backend.knowledge.schemas import KnowledgeSnippet
from backend.advice.schemas import AdviceRequest
from backend.timeline.event_detector import BaseDetector, EventDetectorPipeline
from backend.riot.live_client import GameState
from backend.context.engine import build_context_packet


def test_detected_event_has_required_fields():
    event = DetectedEvent(
        event_type="LOW_HEALTH",
        severity=Severity.HIGH,
        reason="Health is 20%",
        recommended_action="Recall immediately",
    )
    assert event.event_type == "LOW_HEALTH"
    assert event.severity == Severity.HIGH
    assert event.severity.value == 3


def test_severity_ordering():
    assert Severity.HIGH.value > Severity.MEDIUM.value > Severity.LOW.value


def test_knowledge_snippet_fields():
    snippet = KnowledgeSnippet(
        source="champion:rumble",
        content="Rumble has no dash — vulnerable when pushed",
        relevance="high",
    )
    assert snippet.source == "champion:rumble"
    assert snippet.relevance == "high"


def test_advice_request_fields():
    event = DetectedEvent("LOW_HEALTH", Severity.HIGH, "HP 20%", "Recall")
    snippet = KnowledgeSnippet("champion:rumble", "No dash", "high")
    req = AdviceRequest(
        mode="DEFENSIVE",
        priority_event=event,
        knowledge_snippets=[snippet],
        response_length="short",
    )
    assert req.mode == "DEFENSIVE"
    assert req.priority_event.event_type == "LOW_HEALTH"
    assert len(req.knowledge_snippets) == 1


def test_advice_request_no_event():
    req = AdviceRequest(
        mode="MACRO",
        priority_event=None,
        knowledge_snippets=[],
        response_length="medium",
    )
    assert req.priority_event is None


def _make_state(**kwargs) -> GameState:
    defaults = dict(current_health=1000, max_health=2000, gold=500, level=5, game_time=300.0)
    defaults.update(kwargs)
    return GameState(**defaults)


def test_base_detector_raises():
    detector = BaseDetector()
    state = _make_state()
    packet = build_context_packet(state)
    try:
        detector.detect(state, packet)
        assert False, "Should have raised NotImplementedError"
    except NotImplementedError:
        pass


def test_pipeline_returns_empty_with_no_detectors():
    pipeline = EventDetectorPipeline(detectors=[])
    state = _make_state()
    packet = build_context_packet(state)
    assert pipeline.run(state, packet) == []


def test_pipeline_sorts_by_severity_descending():
    class AlwaysLow(BaseDetector):
        def detect(self, state, packet):
            return [DetectedEvent("LOW_SIGNAL", Severity.LOW, "low", "do nothing")]

    class AlwaysHigh(BaseDetector):
        def detect(self, state, packet):
            return [DetectedEvent("HIGH_SIGNAL", Severity.HIGH, "high", "act now")]

    pipeline = EventDetectorPipeline(detectors=[AlwaysLow(), AlwaysHigh()])
    state = _make_state()
    packet = build_context_packet(state)
    events = pipeline.run(state, packet)
    assert events[0].severity == Severity.HIGH
    assert events[1].severity == Severity.LOW
