from backend.advice.schemas import AdviceRequest
from backend.timeline.schemas import DetectedEvent, Severity
from backend.knowledge.schemas import KnowledgeSnippet

# OBJECTIVE_SPAWN intentionally omitted — falls through to "MACRO" default
_MODE_MAP: dict[str, str] = {
    "LOW_HEALTH": "DEFENSIVE",
    "GOLD_SPIKE": "RECALL",
    "DEATH_STREAK": "DEFENSIVE",
}

def plan(events: list[DetectedEvent], snippets: list[KnowledgeSnippet]) -> AdviceRequest:
    top_event = events[0] if events else None
    mode = _decide_mode(top_event)
    length = "short" if top_event and top_event.severity == Severity.HIGH else "medium"
    return AdviceRequest(
        mode=mode,
        priority_event=top_event,
        knowledge_snippets=snippets,
        response_length=length,
    )

def _decide_mode(event: DetectedEvent | None) -> str:
    if not event:
        return "MACRO"
    return _MODE_MAP.get(event.event_type, "MACRO")
