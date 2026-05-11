from backend.timeline.schemas import DetectedEvent, Severity
from backend.knowledge.schemas import KnowledgeSnippet
from backend.advice.schemas import AdviceRequest
from backend.timeline.event_detector import BaseDetector, EventDetectorPipeline
from backend.riot.live_client import GameState
from backend.context.engine import build_context_packet
from backend.timeline.detectors.low_health import LowHealthDetector
from backend.timeline.detectors.gold_spike import GoldSpikeDetector
from backend.timeline.detectors.objective_timer import ObjectiveTimerDetector


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


def test_low_health_detector_fires_below_30_percent():
    detector = LowHealthDetector()
    state = _make_state(current_health=500, max_health=2000)  # 25%
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert len(events) == 1
    assert events[0].event_type == "LOW_HEALTH"
    assert events[0].severity == Severity.HIGH


def test_low_health_detector_silent_above_30_percent():
    detector = LowHealthDetector()
    state = _make_state(current_health=700, max_health=2000)  # 35%
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert events == []


def test_low_health_detector_fires_at_exactly_29_percent():
    detector = LowHealthDetector()
    state = _make_state(current_health=580, max_health=2000)  # 29%
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert len(events) == 1


def test_gold_spike_high_severity_above_2500():
    detector = GoldSpikeDetector()
    state = _make_state(current_health=1500, max_health=2000, gold=2600)
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert len(events) == 1
    assert events[0].event_type == "GOLD_SPIKE"
    assert events[0].severity == Severity.HIGH


def test_gold_spike_medium_severity_between_1300_and_2500():
    detector = GoldSpikeDetector()
    state = _make_state(current_health=1500, max_health=2000, gold=1800)
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert len(events) == 1
    assert events[0].event_type == "GOLD_SPIKE"
    assert events[0].severity == Severity.MEDIUM


def test_gold_spike_silent_below_1300():
    detector = GoldSpikeDetector()
    state = _make_state(current_health=1500, max_health=2000, gold=1200)
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert events == []


def test_gold_spike_fires_at_exactly_1300():
    detector = GoldSpikeDetector()
    state = _make_state(current_health=1500, max_health=2000, gold=1300)
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert len(events) == 1


def test_objective_fires_60s_before_first_dragon():
    # game_time = 4:10 (250s) — 50s before Dragon first spawn at 5:00 (300s)
    detector = ObjectiveTimerDetector()
    state = _make_state(game_time=250.0)
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    event_types = [e.event_type for e in events]
    assert "OBJECTIVE_SPAWN" in event_types
    matching = [e for e in events if e.event_type == "OBJECTIVE_SPAWN"]
    assert any("Dragon" in e.reason for e in matching)


def test_objective_silent_before_60s_window():
    # game_time = 3:00 (180s) — 2 min before Dragon
    detector = ObjectiveTimerDetector()
    state = _make_state(game_time=180.0)
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    assert events == []


def test_objective_fires_60s_before_first_baron():
    # game_time = 19:10 (1150s) — 50s before Baron first spawn at 20:00 (1200s)
    detector = ObjectiveTimerDetector()
    state = _make_state(game_time=1150.0)
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    event_types = [e.event_type for e in events]
    assert "OBJECTIVE_SPAWN" in event_types
    matching = [e for e in events if e.event_type == "OBJECTIVE_SPAWN"]
    assert any("Baron" in e.reason for e in matching)


def test_objective_dragon_respawn_after_kill():
    # DragonKill at 5.0m (300s) → respawn at 10:00 (600s)
    # game_time = 9:10 (550s) — 50s before respawn
    detector = ObjectiveTimerDetector()
    state = _make_state(
        game_time=550.0,
        recent_events=("DragonKill at 5.0m",),
    )
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    event_types = [e.event_type for e in events]
    assert "OBJECTIVE_SPAWN" in event_types


def test_objective_voidgrubs_despawn_warning():
    # game_time = 14:10 (850s) — Voidgrubs despawn at 14:45 (885s), within 60s
    detector = ObjectiveTimerDetector()
    state = _make_state(game_time=850.0, recent_events=())
    packet = build_context_packet(state)
    events = detector.detect(state, packet)
    event_types = [e.event_type for e in events]
    assert "OBJECTIVE_SPAWN" in event_types
    matching = [e for e in events if e.event_type == "OBJECTIVE_SPAWN"]
    assert any("Voidgrub" in e.reason for e in matching)


def test_objective_no_alert_after_voidgrubs_killed():
    # Voidgrubs already killed — no alert
    detector = ObjectiveTimerDetector()
    state = _make_state(
        game_time=850.0,
        recent_events=("VoidgrubKill at 9.0m",),
    )
    packet = build_context_packet(state)
    events = [e for e in detector.detect(state, packet) if "Voidgrub" in e.reason]
    assert events == []
