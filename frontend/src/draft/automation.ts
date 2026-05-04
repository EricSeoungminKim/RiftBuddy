export function shouldFetchRoleRecommendations(inProgress: boolean): boolean {
  return inProgress;
}

export function championForMatchups(
  allyChampions: string[],
  selectedSlotIndex: number,
  recommendedChampion: string,
): string {
  return allyChampions[selectedSlotIndex] || recommendedChampion;
}

export interface MatchupRow {
  myChampion: string;
  enemyChampion: string;
}

export function matchupForEnemy<T extends MatchupRow>(
  matchups: Record<number, T>,
  currentChampion: string,
  enemyChampion: string,
): T | undefined {
  return Object.values(matchups).find(
    (matchup) => matchup.myChampion === currentChampion && matchup.enemyChampion === enemyChampion,
  );
}

export function matchupWinRateFromResponse(raw: unknown): number | undefined {
  if (!raw || typeof raw !== "object") return undefined;
  const value = (raw as { winRate?: unknown }).winRate;
  if (typeof value === "number") return toOneDecimal(value > 1 ? value : value * 100);
  if (typeof value === "string") {
    const parsed = Number(value.replace("%", ""));
    return Number.isFinite(parsed) ? toOneDecimal(parsed) : undefined;
  }
  return undefined;
}

function toOneDecimal(value: number): number {
  return Math.round(value * 10) / 10;
}

export function championForBanCounters(allyChampions: string[], selectedSlotIndex: number): string {
  return allyChampions[selectedSlotIndex] || "";
}

export function shouldFetchTeamStrategy(
  allyChampions: string[],
  enemyChampions: string[],
  allyCompleted: boolean[] = allyChampions.map(Boolean),
  enemyCompleted: boolean[] = enemyChampions.map(Boolean),
): boolean {
  const allyReady = allyChampions.slice(0, 5).every((champion, index) => Boolean(champion) && allyCompleted[index] !== false);
  const enemyReady = enemyChampions.slice(0, 5).every((champion, index) => Boolean(champion) && enemyCompleted[index] !== false);
  return allyChampions.length >= 5 && enemyChampions.length >= 5 && allyReady && enemyReady;
}
