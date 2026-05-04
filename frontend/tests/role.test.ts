import assert from "node:assert/strict";
import test from "node:test";

import { resolveSelectedRole, roleLabel } from "../src/draft/role";

test("resolveSelectedRole uses the selected slot role instead of the initial fallback", () => {
  assert.equal(resolveSelectedRole(["탑", "정글", "미드", "바텀", "서폿"], 2, "바텀"), "미드");
});

test("resolveSelectedRole keeps the current role when selected slot cannot be resolved", () => {
  assert.equal(resolveSelectedRole(["탑", "정글", "미드", "바텀", "서폿"], -1, "정글"), "정글");
});

test("roleLabel maps LCU assigned positions to Korean role labels", () => {
  assert.equal(roleLabel({ assignedPosition: "utility" }, "서폿"), "서폿");
  assert.equal(roleLabel({ assignedPosition: "middle" }, "미드"), "미드");
});
