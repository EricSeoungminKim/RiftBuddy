import json
from pathlib import Path

from backend.knowledge.schemas import KnowledgeSnippet


def load_champion_snippets(data_dir: Path) -> list[KnowledgeSnippet]:
    snippets: list[KnowledgeSnippet] = []
    for json_file in sorted(data_dir.glob("*.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        champion = data["champion"]
        gp = data["gameplan"]
        gameplan_text = (
            f"Gameplan: {gp['summary']} "
            f"Power spikes: {', '.join(gp['power_spikes'])}. "
            f"Win condition: {gp['win_condition']} "
            f"Early game: {gp['early_game']} "
            f"Positioning: {gp['positioning']}"
        )
        snippets.append(KnowledgeSnippet(
            source=f"champion:{champion}:gameplan",
            content=gameplan_text,
            relevance="high",
        ))
        for enemy, matchup in data.get("matchups", {}).items():
            matchup_text = (
                f"Matchup vs {enemy} (difficulty: {matchup['difficulty']}): "
                f"{matchup['tips']} "
                f"Power shift: {matchup['power_shift']}"
            )
            snippets.append(KnowledgeSnippet(
                source=f"champion:{champion}:matchup:{enemy}",
                content=matchup_text,
                relevance="high",
            ))
    return snippets
