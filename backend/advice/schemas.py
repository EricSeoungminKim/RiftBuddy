from __future__ import annotations
from dataclasses import dataclass, field
from backend.timeline.schemas import DetectedEvent
from backend.knowledge.schemas import KnowledgeSnippet


@dataclass
class AdviceRequest:
    mode: str                                    # "DEFENSIVE", "AGGRESSIVE", "MACRO", "RECALL"
    priority_event: DetectedEvent | None
    knowledge_snippets: list[KnowledgeSnippet]   = field(default_factory=list)
    response_length: str                         = "medium"  # "short" or "medium"
