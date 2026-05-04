import assert from "node:assert/strict";
import test from "node:test";

import { DDRAGON_VERSION, championAssetId, championIconUrl } from "../src/draft/championAssets";

test("uses the current DDragon version that includes newer champions", () => {
  assert.equal(DDRAGON_VERSION, "16.9.1");
  assert.equal(championIconUrl("Ambessa"), "https://ddragon.leagueoflegends.com/cdn/16.9.1/img/champion/Ambessa.png");
  assert.equal(championIconUrl("Yunara"), "https://ddragon.leagueoflegends.com/cdn/16.9.1/img/champion/Yunara.png");
});

test("normalizes special champion ids for DDragon icon paths", () => {
  assert.equal(championAssetId("Kai'Sa"), "Kaisa");
  assert.equal(championAssetId("KaiSa"), "Kaisa");
  assert.equal(championAssetId("Kha'Zix"), "Khazix");
  assert.equal(championAssetId("XINZHAO"), "XinZhao");
  assert.equal(championAssetId("LeeSin"), "LeeSin");
});
