from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.riot.live_client import GameState

MAX_SNAPSHOTS = 120


@dataclass
class GameSession:
    snapshots: list["GameState"] = field(default_factory=list)
    seed_doc_id: str | None = None

    def add_snapshot(self, state: "GameState") -> None:
        if len(self.snapshots) >= MAX_SNAPSHOTS:
            self.snapshots.pop(0)
        self.snapshots.append(state)

    def clear(self) -> None:
        self.snapshots.clear()
        self.seed_doc_id = None

    @property
    def is_empty(self) -> bool:
        return len(self.snapshots) == 0

    def summary_lines(self) -> list[str]:
        lines = []
        prev_gold = 0.0
        prev_cs = 0
        for s in self.snapshots:
            minutes = int(s.game_time // 60)
            seconds = int(s.game_time % 60)
            timestamp = f"{minutes}:{seconds:02d}"
            hp_pct = round((s.current_health / s.max_health) * 100, 1) if s.max_health else 0
            recent = getattr(s, "recent_events", ())
            gold_delta = s.gold - prev_gold if prev_gold else 0
            cs_delta = s.creep_score - prev_cs if prev_cs else 0
            prev_gold = s.gold
            prev_cs = s.creep_score
            lines.append(
                f"[{timestamp}] {s.champion_name} ({s.assigned_position}) | "
                f"HP {hp_pct}% | 골드 {s.gold:g} (팀차이 {s.gold_diff:+g}) | "
                f"KDA {s.kills}/{s.deaths}/{s.assists} | CS {s.creep_score} | "
                f"이벤트: {', '.join(recent) if recent else '없음'}"
            )
        return lines
