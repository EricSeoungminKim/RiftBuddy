export const ROLES = ['탑', '정글', '미드', '바텀', '서폿'] as const;

export type Role = (typeof ROLES)[number];

export interface RoleSlot {
  cellId?: number;
  assignedPosition?: string;
}

const ROLE_BY_LCU: Record<string, Role> = {
  top: '탑',
  jungle: '정글',
  middle: '미드',
  bottom: '바텀',
  utility: '서폿',
};

export function roleLabel(slot: Pick<RoleSlot, 'assignedPosition'> | undefined, fallback: Role): Role {
  const raw = slot?.assignedPosition?.toLowerCase();
  return raw ? ROLE_BY_LCU[raw] ?? fallback : fallback;
}

export function findLocalPlayerSlotIndex(slots: RoleSlot[], myCell: number): number {
  if (myCell < 0) return -1;
  return slots.findIndex((slot) => slot.cellId === myCell);
}

export function resolveSelectedRole(roleLabels: Role[], selectedSlotIndex: number, currentRole: Role): Role {
  if (selectedSlotIndex < 0) return currentRole;
  return roleLabels[selectedSlotIndex] ?? currentRole;
}
