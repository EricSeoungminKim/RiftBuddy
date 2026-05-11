from dataclasses import dataclass


@dataclass
class KnowledgeSnippet:
    source: str    # e.g. "champion:rumble", "matchup:rumble_vs_tryndamere", "user_plan"
    content: str   # text injected into LLM context
    relevance: str # "high" or "medium"
