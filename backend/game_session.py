from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.riot.live_client import GameState

MAX_SNAPSHOTS = 60


@dataclass
class GameSession:
    snapshots: list["GameState"] = field(default_factory=list)

    def add_snapshot(self, state: "GameState") -> None:
        if len(self.snapshots) >= MAX_SNAPSHOTS:
            self.snapshots.pop(0)
        self.snapshots.append(state)

    def clear(self) -> None:
        self.snapshots.clear()

    @property
    def is_empty(self) -> bool:
        return len(self.snapshots) == 0

    def summary_lines(self) -> list[str]:
        lines = []
        for s in self.snapshots:
            minutes = int(s.game_time // 60)
            seconds = int(s.game_time % 60)
            timestamp = f"{minutes}:{seconds:02d}"
            hp_pct = round((s.current_health / s.max_health) * 100, 1) if s.max_health else 0
            recent = getattr(s, "recent_events", ())
            lines.append(
                f"[{timestamp}] 챔피언 {s.champion_name} | HP {hp_pct}% | "
                f"골드 {s.gold:g} | 킬 {s.kills}/{s.deaths}/{s.assists} | "
                f"CS {s.creep_score} | 최근이벤트: {', '.join(recent) if recent else '없음'}"
            )
        return lines
