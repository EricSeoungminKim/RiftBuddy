export interface ChampSelectVisibilityState {
  shouldShowDraft: boolean;
  wasInChampSelect: boolean;
}

export interface DraftContextPayload {
  my_champion: string;
  my_position: string;
  lane_opponent: string | null;
}

interface ChampSelectSlot {
  cellId: number;
  slot: number;
  champion: string;
  assignedPosition: string;
}

interface ChampSelectStatus {
  myCell: number;
  allySlots: ChampSelectSlot[];
  enemySlots: ChampSelectSlot[];
}

const POSITION_BY_LCU: Record<string, string> = {
  top: "TOP",
  jungle: "JUNGLE",
  middle: "MIDDLE",
  bottom: "BOTTOM",
  utility: "UTILITY",
};

export function nextChampSelectVisibilityState(
  inProgress: boolean,
  previousWasInChampSelect: boolean,
  draftVisible: boolean,
): ChampSelectVisibilityState {
  if (!inProgress) {
    return { shouldShowDraft: false, wasInChampSelect: false };
  }
  return {
    shouldShowDraft: !previousWasInChampSelect || !draftVisible,
    wasInChampSelect: true,
  };
}

export function draftContextFromChampSelectStatus(status: ChampSelectStatus): DraftContextPayload | null {
  const mySlotIndex = status.allySlots.findIndex((slot) => slot.cellId === status.myCell);
  if (mySlotIndex < 0) return null;

  const mySlot = status.allySlots[mySlotIndex];
  if (!mySlot?.champion) return null;

  const position = normalizePosition(mySlot.assignedPosition);
  const laneOpponent = opponentForPosition(status.enemySlots, position, mySlotIndex);
  return {
    my_champion: mySlot.champion,
    my_position: position,
    lane_opponent: laneOpponent,
  };
}

function normalizePosition(position: string): string {
  return POSITION_BY_LCU[position.toLowerCase()] ?? position.toUpperCase();
}

function opponentForPosition(
  enemySlots: ChampSelectSlot[],
  position: string,
  fallbackIndex: number,
): string | null {
  const sameRole = enemySlots.find((slot) => normalizePosition(slot.assignedPosition) === position && slot.champion);
  if (sameRole) return sameRole.champion;
  return enemySlots[fallbackIndex]?.champion || null;
}
