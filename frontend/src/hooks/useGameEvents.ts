// frontend/src/hooks/useGameEvents.ts
import { useState, useEffect } from "react";

export interface ObjectiveTimer {
  name: string;
  spawnAt: number;
  respawn: number;
  lastKillAt: number | null;
  alive: boolean;
}

export interface BuffHolder {
  buffName: string;
  championName: string;
  team: "ally" | "enemy";
  expiresAt: number;
}

export interface UltTimer {
  championName: string;
  team: "ally" | "enemy";
  lastUsedAt: number | null;
  baseCd: number;
  cdr: number;
}

export interface GameEvents {
  gameTime: number;
  objectives: ObjectiveTimer[];
  buffs: BuffHolder[];
  ults: UltTimer[];
  allyGold: number;
  enemyGold: number;
  goldDiff: number;
  allyChampions: string[];
  enemyChampions: string[];
}

const INITIAL_OBJECTIVES: ObjectiveTimer[] = [
  { name: "Dragon", spawnAt: 300, respawn: 300, lastKillAt: null, alive: true },
  { name: "Baron", spawnAt: 1200, respawn: 360, lastKillAt: null, alive: false },
  { name: "Herald", spawnAt: 480, respawn: 0, lastKillAt: null, alive: true },
  { name: "Scuttler", spawnAt: 90, respawn: 150, lastKillAt: null, alive: true },
];

const DEFAULT_EVENTS: GameEvents = {
  gameTime: 0,
  objectives: INITIAL_OBJECTIVES,
  buffs: [],
  ults: [],
  allyGold: 0,
  enemyGold: 0,
  goldDiff: 0,
  allyChampions: [],
  enemyChampions: [],
};

export function useGameEvents(wsMessages: Array<{ role: string; text: string }>): GameEvents {
  const [events, setEvents] = useState<GameEvents>(DEFAULT_EVENTS);

  useEffect(() => {
    const last = [...wsMessages].reverse().find((m) => m.role === "system" && m.text.startsWith("{"));
    if (!last) return;
    try {
      const parsed = JSON.parse(last.text) as Partial<GameEvents>;
      setEvents((prev) => ({ ...prev, ...parsed }));
    } catch {
      // not a game event message — ignore
    }
  }, [wsMessages]);

  return events;
}
