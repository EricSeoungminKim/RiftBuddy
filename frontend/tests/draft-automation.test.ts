import assert from "node:assert/strict";
import test from "node:test";

import {
  championForBanCounters,
  championForMatchups,
  matchupWinRateFromResponse,
  matchupForEnemy,
  shouldFetchRoleRecommendations,
  shouldFetchTeamStrategy,
} from "../src/draft/automation";

test("does not request role recommendations before champ select starts", () => {
  assert.equal(shouldFetchRoleRecommendations(false), false);
});

test("requests role recommendations during active champ select", () => {
  assert.equal(shouldFetchRoleRecommendations(true), true);
});

test("uses selected ally champion for opponent matchup lookups", () => {
  assert.equal(championForMatchups(["Shyvana", "Nami", "Galio"], 2, "Ahri"), "Galio");
});

test("uses the current player champion over a recommended champion for matchup source", () => {
  assert.equal(championForMatchups(["Qiyana", "Velkoz", "Gangplank", "Caitlyn"], 3, "Ashe"), "Caitlyn");
});

test("falls back to recommended champion before player pick is known", () => {
  assert.equal(championForMatchups(["Shyvana", "Nami", ""], 2, "Ahri"), "Ahri");
});

test("uses selected ally champion for ban counter lookup", () => {
  assert.equal(championForBanCounters(["Shyvana", "Nami", "Galio"], 2), "Galio");
});

test("matchup rows ignore stale data from a different player champion", () => {
  const matchups = {
    0: { myChampion: "Ashe", enemyChampion: "Sivir", role: "바텀", winRate: 53.8, raw: {} },
    1: { myChampion: "Caitlyn", enemyChampion: "Sivir", role: "바텀", winRate: 49.2, raw: {} },
  };

  assert.equal(matchupForEnemy(matchups, "Caitlyn", "Sivir")?.winRate, 49.2);
  assert.equal(matchupForEnemy(matchups, "Jinx", "Sivir"), undefined);
});

test("frontend only trusts backend top-level matchup win rate", () => {
  assert.equal(matchupWinRateFromResponse({ winRate: 0.533 }), 53.3);
  assert.equal(matchupWinRateFromResponse({ winRate: 48.3 }), 48.3);
  assert.equal(
    matchupWinRateFromResponse({ data: { summary: { average_stats: { win_rate: 0.483 } } } }),
    undefined,
  );
});

test("team strategy waits until both teams have five champions", () => {
  assert.equal(shouldFetchTeamStrategy(["A", "B", "C", "D", "E"], ["F", "G", "H", "I", "J"]), true);
  assert.equal(shouldFetchTeamStrategy(["A", "B", "C", "D", ""], ["F", "G", "H", "I", "J"]), false);
  assert.equal(
    shouldFetchTeamStrategy(
      ["A", "B", "C", "D", "E"],
      ["F", "G", "H", "I", "J"],
      [true, true, true, true, true],
      [true, true, false, true, true],
    ),
    false,
  );
});
