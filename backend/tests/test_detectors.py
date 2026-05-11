from backend.timeline.schemas import DetectedEvent, Severity


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
