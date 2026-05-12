"""Convert OP.GG API responses into KnowledgeSnippets for the RAG pipeline."""
from __future__ import annotations

from backend.knowledge.schemas import KnowledgeSnippet


def matchup_guide_to_snippet(data: dict, my_champion: str, opponent: str) -> KnowledgeSnippet | None:
    if not data:
        return None
    summary = data.get("data", {}).get("summary", {})
    stats = summary.get("average_stats", {})
    win_rate = stats.get("win_rate")
    tier = stats.get("tier_data", {}).get("tier")

    positions = summary.get("positions", [])
    counters = []
    for pos in positions:
        counters = pos.get("counters", [])
        break

    parts = [f"[OP.GG 매치업] {my_champion} vs {opponent}:"]
    if win_rate is not None:
        pct = round(win_rate * 100, 1)
        parts.append(f"승률 {pct}%")
    if tier is not None:
        parts.append(f"티어 {tier}")
    if counters:
        counter_names = [c["champion_name"] for c in counters[:3]]
        parts.append(f"카운터: {', '.join(counter_names)}")

    spells = data.get("data", {}).get("summoner_spells", [])
    if spells:
        best_spell = spells[0]
        spell_names = best_spell.get("ids_names", [])
        parts.append(f"추천 스펠: {'+'.join(spell_names)}")

    core = data.get("data", {}).get("core_items", [])
    if core:
        best_core = core[0]
        item_names = best_core.get("ids_names", [])
        parts.append(f"코어 아이템: {' → '.join(item_names)}")

    return KnowledgeSnippet(
        source=f"opgg:matchup:{my_champion.lower()}_vs_{opponent.lower()}",
        content=" | ".join(parts),
        relevance="high",
    )


def counters_to_snippet(data: dict, champion: str) -> KnowledgeSnippet | None:
    if not data:
        return None
    d = data.get("data", {})
    strong = d.get("strong_counters", [])
    weak = d.get("weak_counters", [])

    parts = [f"[OP.GG 카운터] {champion}:"]
    if strong:
        names = [c["champion_name"] for c in strong[:3]]
        parts.append(f"불리한 상대: {', '.join(names)}")
    if weak:
        names = [c["champion_name"] for c in weak[:3]]
        parts.append(f"유리한 상대: {', '.join(names)}")

    if len(parts) == 1:
        return None

    return KnowledgeSnippet(
        source=f"opgg:counters:{champion.lower()}",
        content=" | ".join(parts),
        relevance="medium",
    )
