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


def fed_enemy_to_snippet(data: dict, fed_champion: str) -> KnowledgeSnippet | None:
    """Snippet focused on how to play against the most fed enemy."""
    if not data:
        return None
    d = data.get("data", {})
    strong = d.get("strong_counters", [])
    summary = d.get("summary", {}).get("average_stats", {})
    win_rate = summary.get("win_rate")

    parts = [f"[OP.GG 주의] 가장 큰 상대 {fed_champion}:"]
    if win_rate is not None:
        pct = round(win_rate * 100, 1)
        parts.append(f"현재 패치 승률 {pct}%")
    if strong:
        names = [c["champion_name"] for c in strong[:3]]
        parts.append(f"이 챔피언을 카운터하는 픽: {', '.join(names)}")
    parts.append("교전 피하고 팀과 함께 대응")

    return KnowledgeSnippet(
        source=f"opgg:fed_enemy:{fed_champion.lower()}",
        content=" | ".join(parts),
        relevance="high",
    )
