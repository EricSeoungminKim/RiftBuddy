import pytest
from backend.advice.planner import plan
from backend.advice.schemas import AdviceRequest
from backend.timeline.schemas import DetectedEvent, Severity
from backend.knowledge.schemas import KnowledgeSnippet


class TestPlan:
    """Test suite for the advice planner module."""

    def test_empty_events_returns_macro(self):
        """Empty events should default to MACRO mode with medium response."""
        result = plan([], [])

        assert isinstance(result, AdviceRequest)
        assert result.mode == "MACRO"
        assert result.priority_event is None
        assert result.response_length == "medium"

    def test_low_health_high_severity(self):
        """LOW_HEALTH event with HIGH severity should trigger DEFENSIVE mode and short response."""
        event = DetectedEvent(
            event_type="LOW_HEALTH",
            severity=Severity.HIGH,
            reason="Player health below 25%",
            recommended_action="Back away and play safe"
        )

        result = plan([event], [])

        assert isinstance(result, AdviceRequest)
        assert result.mode == "DEFENSIVE"
        assert result.response_length == "short"
        assert result.priority_event == event

    def test_gold_spike_medium_severity(self):
        """GOLD_SPIKE event with MEDIUM severity should trigger RECALL mode."""
        event = DetectedEvent(
            event_type="GOLD_SPIKE",
            severity=Severity.MEDIUM,
            reason="Gold threshold reached",
            recommended_action="Recall to spend gold"
        )

        result = plan([event], [])

        assert isinstance(result, AdviceRequest)
        assert result.mode == "RECALL"
        assert result.response_length == "medium"
        assert result.priority_event == event

    def test_death_streak_high_severity(self):
        """DEATH_STREAK event with HIGH severity should trigger DEFENSIVE mode and short response."""
        event = DetectedEvent(
            event_type="DEATH_STREAK",
            severity=Severity.HIGH,
            reason="Player has died 3 times",
            recommended_action="Play under tower"
        )

        result = plan([event], [])

        assert isinstance(result, AdviceRequest)
        assert result.mode == "DEFENSIVE"
        assert result.response_length == "short"
        assert result.priority_event == event

    def test_objective_spawn_low_severity(self):
        """OBJECTIVE_SPAWN event with LOW severity should default to MACRO mode."""
        event = DetectedEvent(
            event_type="OBJECTIVE_SPAWN",
            severity=Severity.LOW,
            reason="Baron spawned",
            recommended_action="Check map"
        )

        result = plan([event], [])

        assert isinstance(result, AdviceRequest)
        assert result.mode == "MACRO"
        assert result.response_length == "medium"
        assert result.priority_event == event

    def test_unknown_event_type_defaults_macro(self):
        """Unknown event types should default to MACRO mode."""
        event = DetectedEvent(
            event_type="WARD_KILL",
            severity=Severity.MEDIUM,
            reason="Ward destroyed",
            recommended_action="Look for stealth"
        )

        result = plan([event], [])

        assert isinstance(result, AdviceRequest)
        assert result.mode == "MACRO"
        assert result.response_length == "medium"
        assert result.priority_event == event

    def test_knowledge_snippets_passed_through(self):
        """Knowledge snippets should be preserved in the result."""
        snippet1 = KnowledgeSnippet(
            source="champion:rumble",
            content="Rumble is strong in teamfights",
            relevance="high"
        )
        snippet2 = KnowledgeSnippet(
            source="matchup:rumble_vs_tryndamere",
            content="Tryndamere wins 1v1 early",
            relevance="medium"
        )
        event = DetectedEvent(
            event_type="LOW_HEALTH",
            severity=Severity.HIGH,
            reason="Low on health",
            recommended_action="Back"
        )

        result = plan([event], [snippet1, snippet2])

        assert isinstance(result, AdviceRequest)
        assert len(result.knowledge_snippets) == 2
        assert result.knowledge_snippets[0] == snippet1
        assert result.knowledge_snippets[1] == snippet2

    def test_priority_event_is_first_event(self):
        """When multiple events provided, priority_event should be the first one."""
        event1 = DetectedEvent(
            event_type="LOW_HEALTH",
            severity=Severity.HIGH,
            reason="Health low",
            recommended_action="Back"
        )
        event2 = DetectedEvent(
            event_type="GOLD_SPIKE",
            severity=Severity.MEDIUM,
            reason="Gold high",
            recommended_action="Recall"
        )

        result = plan([event1, event2], [])

        assert isinstance(result, AdviceRequest)
        assert result.priority_event == event1
