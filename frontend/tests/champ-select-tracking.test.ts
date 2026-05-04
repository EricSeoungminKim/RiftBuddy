import assert from "node:assert/strict";
import test from "node:test";

import { nextChampSelectVisibilityState } from "../electron/champSelectTracking";

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
