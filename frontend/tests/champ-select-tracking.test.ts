import assert from "node:assert/strict";
import test from "node:test";

import {
  draftContextFromChampSelectStatus,
  nextChampSelectVisibilityState,
} from "../electron/champSelectTracking";

test("resets tracking when champ select ends through a normal 200 response", () => {
  assert.deepEqual(
    nextChampSelectVisibilityState(false, true, false),
    { shouldShowDraft: false, wasInChampSelect: false },
  );
});

test("reopens draft window when champ select is active but the window is hidden", () => {
  assert.deepEqual(
    nextChampSelectVisibilityState(true, true, false),
    { shouldShowDraft: true, wasInChampSelect: true },
  );
});

test("builds draft context from local player slot and matching enemy role", () => {
  assert.deepEqual(
    draftContextFromChampSelectStatus({
      myCell: 2,
      allySlots: [
        { cellId: 1, slot: 0, champion: "LeeSin", assignedPosition: "jungle" },
        { cellId: 2, slot: 1, champion: "Rumble", assignedPosition: "top" },
      ],
      enemySlots: [
        { cellId: 6, slot: 0, champion: "Ahri", assignedPosition: "middle" },
        { cellId: 7, slot: 1, champion: "Darius", assignedPosition: "top" },
      ],
    }),
    { my_champion: "Rumble", my_position: "TOP", lane_opponent: "Darius" },
  );
});

test("draft context falls back to mirrored enemy slot when role is unknown", () => {
  assert.deepEqual(
    draftContextFromChampSelectStatus({
      myCell: 2,
      allySlots: [
        { cellId: 1, slot: 0, champion: "LeeSin", assignedPosition: "jungle" },
        { cellId: 2, slot: 1, champion: "Rumble", assignedPosition: "top" },
      ],
      enemySlots: [
        { cellId: 6, slot: 0, champion: "Ahri", assignedPosition: "" },
        { cellId: 7, slot: 1, champion: "Darius", assignedPosition: "" },
      ],
    }),
    { my_champion: "Rumble", my_position: "TOP", lane_opponent: "Darius" },
  );
});
