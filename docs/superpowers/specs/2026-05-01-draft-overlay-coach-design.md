# RiftBuddy: Draft Window + Overlay Enhancements + Post-game Coach Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a draft-phase analysis window, enhanced in-game overlay tabs, and a post-game coaching screen to RiftBuddy.

**Architecture:** Two Electron windows share one FastAPI backend. Draft Window is a framed React page (~1200×800) for champ select and post-game. In-game overlay is the existing transparent window, extended with tabbed panels. Backend gains new HTTP endpoints proxying op.gg MCP and storing GameState snapshots.

**Tech Stack:** Electron 28, React 18, TypeScript, FastAPI, op.gg MCP (streaming HTTP), DDragon CDN (static champion/rune images), existing Groq/Claude LLM, existing WebSocket loop.

---

## Sub-project Order

Build in this sequence — each is independently testable:

1. **Sub-project A:** Draft Window (champ select + post-lock-in screens)
2. **Sub-project B:** Post-game Coach screen (same window, screen 3)
3. **Sub-project C:** In-game Overlay tab enhancements

This spec covers all three. Each gets its own implementation plan.

---

## System Architecture

```
Electron Main Process
├── Window 1: Draft Window (framed, 1200×800, always-on-top)
│   ├── Screen 1: Draft Phase  (champ select input + analysis)
│   ├── Screen 2: Post Lock-in (runes + team strategy + matchup)
│   └── Screen 3: Post-game Coach (strengths / improvements / goals)
│
└── Window 2: In-game Overlay (transparent, 520×400, click-through)
    ├── Tab: AI      (existing chat panel)
    ├── Tab: Timers  (dragon/baron/herald/jungle respawns)
    ├── Tab: Gold    (ally vs enemy gold tracker per player)
    ├── Tab: Buffs   (baron/dragon buff holders + time remaining)
    └── Tab: Ults    (ally ultimate cooldown tracker)

FastAPI Backend (existing + additions)
├── Existing: GET  /health
├── Existing: WS   /ws  (in-game loop → overlay AI tab)
├── New:      GET  /draft/champion-analysis?champion=&role=
├── New:      GET  /draft/matchup?my_champion=&enemy_champion=&role=
├── New:      GET  /draft/runes?champion=&role=
├── New:      POST /draft/team-strategy  (body: full draft)
├── New:      POST /game/snapshot        (store GameState during game)
├── New:      POST /postgame/coach       (LLM analysis of snapshots)
└── New:      DELETE /game/snapshots     (clear after coach generated)

External
├── op.gg MCP  https://mcp-api.op.gg/mcp  (champion stats, matchups, runes)
└── DDragon CDN  https://ddragon.leagueoflegends.com  (champion/rune images)
```

### Game State Detection Flow

```
App launch
  → Draft Window opens (Screen 1)
  → Backend polls Live Client every 3s

Live Client returns data (game started)
  → Overlay window activates / shows
  → Draft Window minimizes
  → Backend begins storing GameState snapshots every 30s

Live Client returns 404 (game ended)
  → Backend triggers POST /postgame/coach with all snapshots
  → Draft Window restores, shows Screen 3 (Post-game Coach)
  → Overlay hides
  → Backend clears snapshots

User clicks "새 경기 시작"
  → Draft Window resets to Screen 1
```

---

## Sub-project A: Draft Window

### Screen 1 — Draft Phase

**Layout (1200×800, dark #0f1117 background):**

```
┌──────────────────────────────────────────────────────────────────┐
│  ALLY TEAM [icon×5]              vs        ENEMY TEAM [icon×5]  │
│  (grey placeholder circles until picked)                        │
├────────────────┬─────────────────────────┬───────────────────────┤
│ RECOMMENDATIONS│   LANING ANALYSIS       │  SYNERGY / COUNTER    │
│  (left ~25%)   │    (center ~45%)        │   (right ~30%)        │
│                │                         │                       │
│ Top 5 champs   │ My champ vs enemy lane  │ Ally synergy scores   │
│ for my role    │ • Laning strength score │ Enemy counter scores  │
│ sorted by WR%  │ • Early/Mid/Late adv    │ [champion icons]      │
│                │ • AD/AP ratio           │ score numbers         │
│ [icon][name]   │ • Tankiness comparison  │                       │
│ [WR%] [score]  │                         │                       │
│ ×5             │ "Waiting for picks..."  │                       │
│                │  if incomplete          │                       │
└────────────────┴─────────────────────────┴───────────────────────┘
│ Search: [champion name___________]   Role: [TOP ▼]   [분석 시작] │
└──────────────────────────────────────────────────────────────────┘
```

**Behavior:**

- User selects role from dropdown (TOP/JG/MID/BOT/SUP).
- User types ally picks (1–5) and enemy picks (1–5) into champion search fields in the header icon slots.
- On each pick entry, frontend calls `GET /draft/champion-analysis?champion=&role=` and `GET /draft/matchup?my_champion=&enemy_champion=&role=`.
- Recommendations panel updates with top 5 picks for user's role via op.gg MCP `lol_list_lane_meta_champions`.
- Laning analysis populates when user's champion + enemy laner both entered.
- Synergy/counter panel populates when ≥2 ally or ≥2 enemy champions entered.
- Champion icons fetched from DDragon: `https://ddragon.leagueoflegends.com/cdn/14.9.1/img/champion/{ChampionId}.png`
- Loading spinner per panel while fetching.
- Error state: "데이터를 불러올 수 없습니다" if op.gg MCP fails.

**Auto-transition to Screen 2:** when all 10 champion slots filled (5 ally + 5 enemy) OR user clicks "분석 완료" button.

---

### Screen 2 — Post Lock-in

Triggered when draft complete. Same window, React router navigation.

```
┌──────────────────────────────────────────────────────────────────┐
│  확정 드래프트 — 내 챔피언: [Rumble] TOP                         │
│  Ally: [icon×5]    vs    Enemy: [icon×5]                        │
├──────────────────┬───────────────────────────────────────────────┤
│  추천 룬          │  팀 컴프 전략                                 │
│  Primary: [icons] │  • 승리 조건 (teamfight/poke/split)          │
│  Secondary:[icons]│  • 초반 우선순위                             │
│  Shards:  [icons] │  • 핵심 파워 스파이크                        │
│                   │  • 드래프트 유불리 요약                       │
│  [출처: op.gg]    │  (LLM-generated, Korean)                     │
├───────────────────┴──────────────────────────────────────────────┤
│  내 챔피언 매치업: [Rumble] vs [Darius]                          │
│  • 라인전 단계별 분석 (초반/중반/후반)                           │
│  • 유리한 점 / 주의할 점                                        │
│  • 스킬 오더 추천                                               │
│  (from op.gg MCP lol_get_lane_matchup_guide)                    │
└──────────────────────────────────────────────────────────────────┘
│  [← 드래프트로 돌아가기]                    [경기 시작 준비 완료]│
└──────────────────────────────────────────────────────────────────┘
```

**Data sources:**

- Runes: `GET /draft/runes?champion=&role=` → op.gg MCP `lol_get_champion_analysis`.
- Team strategy: `POST /draft/team-strategy` body `{ally: [...], enemy: [...], my_champion, my_role}` → LLM generates Korean paragraph.
- Matchup: `GET /draft/matchup?my_champion=&enemy_champion=&role=` → op.gg MCP `lol_get_lane_matchup_guide`.
- Rune icons: DDragon `https://ddragon.leagueoflegends.com/cdn/img/perk-images/...`

**LCU Rune Auto-Apply:**

Button "룬 자동 적용 ⚠️ (비공식)" appears below the rune panel. Disclaimer shown on first use: "이 기능은 Riot Games의 공식 지원 기능이 아닙니다. LCU API를 사용합니다."

Flow:

1. Backend reads League lockfile to get port + auth token.
2. Calls `GET /lol-perks/v1/currentpage` → gets current rune page ID.
3. Calls `DELETE /lol-perks/v1/pages/{id}` → deletes it (avoids page limit).
4. Calls `POST /lol-perks/v1/pages` with recommended rune page JSON.
5. Returns success → frontend shows "룬이 적용되었습니다 ✓".

Lockfile paths:

- macOS: `/Applications/League of Legends.app/Contents/LoL/lockfile`
- Windows: `C:\Riot Games\League of Legends\lockfile`
- Lockfile format: `ProcessName:PID:Port:Password:Protocol`

LCU auth: Basic auth with `riot:{password}` base64-encoded. `verify=False` for self-signed cert.

Rune page JSON schema:
```json
{
  "name": "RiftBuddy — Rumble TOP",
  "primaryStyleId": 8100,
  "subStyleId": 8300,
  "selectedPerkIds": [8112, 8143, 8138, 8135, 8304, 8345, 5007, 5002, 5001],
  "current": true
}
```

New backend endpoint: `POST /lcu/apply-runes` — body: rune page JSON from op.gg MCP. Returns `{success: bool, message: str}`.

Library: `lcu-driver` (`pip install lcu-driver`) wraps lockfile detection and auth automatically. Use as fallback if manual lockfile read fails.

**Policy note:** Same gray area as Blitz/op.gg desktop. Feature is opt-in, clearly labeled unofficial. No automation of gameplay — only rune page write during champ select.

---

## Sub-project B: Post-game Coach

### Screen 3 — Post-game Coach

Triggered when Live Client returns 404 (game ended). Draft Window restores and navigates here.

```
┌──────────────────────────────────────────────────────────────────┐
│  경기 분석                                                       │
│  [Champion] · [KDA] · CS [n] · [mm:ss 게임 시간]               │
├──────────────────────────┬───────────────────────────────────────┤
│  잘한 점                  │  개선할 점                           │
│  • ...                   │  • ...                               │
│  • ...                   │  • ...                               │
│  • ...                   │  • ...                               │
├──────────────────────────┴───────────────────────────────────────┤
│  핵심 순간들                                                     │
│  • 12:34 — 죽음: 상대 갱에 시야 없이 노출됨                     │
│  • 18:10 — 좋은 귀환 타이밍으로 아이템 스파이크                 │
│  • 24:00 — 바론 시도 타이밍에서 팀원과 합류 실패               │
├──────────────────────────────────────────────────────────────────┤
│  다음 경기 집중 목표                                             │
│  • ...                                                          │
│  • ...                                                          │
└──────────────────────────────────────────────────────────────────┘
│              [새 경기 시작 →]                                    │
└──────────────────────────────────────────────────────────────────┘
```

**Data flow:**

1. During game: backend receives `POST /game/snapshot` every 30s with current `GameState`.
2. On game end (Live Client 404): backend calls `POST /postgame/coach` internally.
3. Coach endpoint: collects all stored snapshots → builds summary prompt → LLM generates structured Korean output.
4. LLM prompt structure:

```
다음은 이번 경기 중 수집된 게임 상태 스냅샷입니다:
[snapshot list: time, health%, gold, KDA, CS, position, recent events]

다음 항목을 한국어로 분석해주세요:
1. 잘한 점 3가지
2. 개선할 점 3가지
3. 핵심 순간 3가지 (타임스탬프 포함)
4. 다음 경기 집중 목표 2가지

JSON 형식으로 응답: {"strengths": [], "improvements": [], "moments": [], "goals": []}
```

5. Frontend parses JSON, renders structured view.
6. "새 경기 시작" → clears snapshots via `DELETE /game/snapshots`, navigates to Screen 1.

**Snapshot storage:** In-memory list in backend (`game_session.py`). Max 60 snapshots (30-min game). Cleared on new game start.

---

## Sub-project C: In-game Overlay Enhancements

### Overlay Layout

Current: single chat panel 520×360, top-right.

New: tabbed panel 520×420. Tab bar at top. Active tab highlighted teal (#00c8a0, matching iTero accent).

```
┌─────────────────────────────────────────┐
│  [AI] [⏱ Timers] [💰 Gold] [🐉 Buffs] [⚡ Ults]  │
├─────────────────────────────────────────┤
│                                         │
│  Active tab content (~360px height)     │
│                                         │
└─────────────────────────────────────────┘
```

**Tab switching:**

- `Cmd+Shift+1` → AI tab
- `Cmd+Shift+2` → Timers tab
- `Cmd+Shift+3` → Gold tab
- `Cmd+Shift+4` → Buffs tab
- `Cmd+Shift+5` → Ults tab
- Click on tab: requires settings mode (`Cmd+Shift+,` disables click-through temporarily for 5s)

**Overlay positioning — League window tracking (Option C):**

Overlay auto-tracks the League of Legends game window. No preset fixed position. Two-step approach:

**Step 1 — Detect League window bounds:**
- Electron main process uses `screen` API + native window enumeration to find the `League of Legends` process window.
- macOS: `AppleScript` via `osascript` — `tell application "System Events" to get position/size of window of process "League of Legends"`
- Windows: `user32.dll` via `node-ffi-napi` or `get-windows` npm package — `FindWindow(NULL, "League of Legends")` + `GetWindowRect`
- Polls every 2s to handle window moves/resizes.
- Stored as `{ x, y, width, height }` in Electron main process state.

**Step 2 — Place panels at HUD-safe zones within League window:**

League HUD layout is fixed relative to window bounds regardless of resolution:

```
League Window (x, y, w, h)
├── TOP-LEFT safe zone:     x+10,       y+10,       w*0.20, h*0.12   ← Timers panel
├── TOP-RIGHT safe zone:    x+w*0.75,   y+10,       w*0.24, h*0.20   ← Gold panel
├── LEFT EDGE safe zone:    x+10,       y+h*0.20,   w*0.18, h*0.55   ← AI chat panel
├── RIGHT EDGE safe zone:   x+w*0.80,   y+h*0.20,   w*0.19, h*0.40  ← Buffs/Ults panel
└── BOTTOM-LEFT safe zone:  x+10,       y+h*0.82,   w*0.25, h*0.16  ← (reserved)
```

Minimap is always bottom-right → never place panels there.
Scoreboard is top-center → panels stay left/right edges.
HUD bar is bottom-center → panels stay above `y+h*0.80`.

**Panel layout per tab:**
- AI chat: LEFT EDGE zone (tall, scrollable)
- Timers: TOP-LEFT zone (compact, 4 rows)
- Gold: TOP-RIGHT zone (table layout)
- Buffs: RIGHT EDGE zone (top portion)
- Ults: RIGHT EDGE zone (bottom portion, or same panel scrollable)

Tab bar rendered as floating pill above the active panel, not a separate fixed bar.

`Cmd+Shift+,` opens settings overlay (disables click-through 5s) to let user adjust zone offsets if needed. Offsets stored in `.env` as `RIFTBUDDY_OVERLAY_OFFSET_X=0` / `RIFTBUDDY_OVERLAY_OFFSET_Y=0`.

---

### Tab: AI (existing, unchanged)

Existing USER/Buddy chat messages. No changes to behavior.

---

### Tab: Timers

Data source: `recent_events` from Live Client (`/liveclientdata/eventdata`).

Tracked timers:

- Dragon: 5min respawn after kill. First spawn at 5:00.
- Baron: 6min respawn after kill. Spawns at 20:00.
- Herald: spawns at 8:00, despawns at 19:45.
- Rift Scuttler: 2.5min respawn.

Display:

```
⏱ OBJECTIVE TIMERS
Dragon    ████░░░░  1:23 remaining
Baron     Not spawned yet (spawns 20:00)
Herald    ████████  Active
Scuttler  ░░░░░░░░  Respawns in 0:45
```

Countdown updates every second via frontend timer (not backend). Backend sends spawn/kill events; frontend calculates countdown.

---

### Tab: Gold

Data source: `ally_gold`, `enemy_gold`, `gold_diff` already in `GameState`. Per-player breakdown from `allPlayers` items + scores.

Display:

```
💰 GOLD TRACKER
              MY TEAM    ENEMY
Total          12,500  « 11,000  (+1,500)
[Rumble icon]   2,800  «  2,600
[Ally 2]        2,400  «  2,200
[Ally 3]        2,500  «  2,300
[Ally 4]        2,200  «  1,900
[Ally 5]        2,600  «  2,000

« = ally ahead  » = enemy ahead
```

Color: green diff if ally ahead, red if behind.

---

### Tab: Buffs

Data source: `recent_events` — detect `DragonKill`, `BaronKill`, `HeraldKill` events with `Stolen` flag.

Display:

```
🐉 MONSTER BUFFS
Baron Buff   [Rumble icon]  4:32 remaining
Dragon Soul  Not yet (need 4 kills)
Dragon #2    [Ally icon]   ACTIVE
```

Baron buff duration: 3.5 min. Dragon buff: permanent soul at 4 stacks.

---

### Tab: Ults

Data source: `allPlayers` champion names + levels from Live Client. CDR from `championStats`.

Cooldown calculation: base ult CD per champion (stored as static JSON `backend/data/ult_cooldowns.json`) minus CDR%.

Display:

```
⚡ ULTIMATE TIMERS
[Rumble]   READY  ✓
[Ally 2]   ░░░░░  0:42 remaining
[Ally 3]   READY  ✓
[Ally 4]   ████░  1:15 remaining
[Ally 5]   READY  ✓
```

Ult used detection: backend emits WebSocket event when a `ChampionKill` or ability event suggests ult fired. Frontend starts countdown. Manual reset if detection unreliable — user can tap champion icon to reset timer.

---

## New Backend Endpoints

### GET /draft/champion-analysis

```python
# Query params: champion (str), role (str)
# Returns: win_rate, pick_rate, ban_rate, tier, counters[], synergies[], recommended_builds[]
# Source: op.gg MCP lol_get_champion_analysis
```

### GET /draft/matchup

```python
# Query params: my_champion (str), enemy_champion (str), role (str)
# Returns: laning_strength, early_advantage, mid_advantage, late_advantage, tips[]
# Source: op.gg MCP lol_get_lane_matchup_guide
```

### GET /draft/runes

```python
# Query params: champion (str), role (str)
# Returns: primary_path, primary_runes[], secondary_path, secondary_runes[], shards[]
# Source: op.gg MCP lol_get_champion_analysis
```

### POST /draft/team-strategy

```python
# Body: {ally: [str×5], enemy: [str×5], my_champion: str, my_role: str}
# Returns: {strategy: str}  # Korean LLM paragraph
# Source: LLM (same advisor as in-game)
```

### POST /game/snapshot

```python
# Body: GameState as JSON
# Appends to in-memory session list
# Called by backend every 30s during active game (internal, not from frontend)
```

### POST /postgame/coach

```python
# No body — reads stored snapshots
# Returns: {strengths: [], improvements: [], moments: [], goals: []}
# Source: LLM with structured JSON prompt
```

### DELETE /game/snapshots

```python
# Clears in-memory snapshot list
# Called on new game start
```

---

## New Frontend Files

```
frontend/src/
├── pages/
│   ├── DraftPage.tsx          # Screen 1: draft phase
│   ├── PostLockInPage.tsx     # Screen 2: runes + strategy
│   └── PostGamePage.tsx       # Screen 3: coaching
├── components/
│   ├── draft/
│   │   ├── ChampionSlot.tsx   # single pick/ban slot with search
│   │   ├── RecommendPanel.tsx # top 5 recommendations
│   │   ├── LaningPanel.tsx    # laning strength analysis
│   │   └── SynergyPanel.tsx   # synergy/counter scores
│   └── overlay/
│       ├── TabBar.tsx         # tab switcher
│       ├── TimersTab.tsx      # objective countdown timers
│       ├── GoldTab.tsx        # team gold tracker
│       ├── BuffsTab.tsx       # baron/dragon buff holders
│       └── UltsTab.tsx        # ultimate cooldown tracker
└── hooks/
    ├── useDraftAnalysis.ts    # fetches /draft/* endpoints
    └── useGameDetection.ts    # polls Live Client to detect game state
```

---

## New Backend Files

```
backend/
├── draft/
│   ├── __init__.py
│   ├── router.py              # FastAPI router for /draft/* endpoints
│   └── opgg_client.py         # op.gg MCP HTTP client
├── game_session.py            # in-memory snapshot store
└── data/
    └── ult_cooldowns.json     # static base ult CDs per champion
```

---

## op.gg MCP Integration

op.gg MCP endpoint: `https://mcp-api.op.gg/mcp` (streaming HTTP, SSE).

Backend calls it via `httpx` with SSE parsing. No API key required per op.gg MCP README.

```python
# NOTE: Implementer must verify exact MCP call format from https://github.com/opgginc/opgg-mcp
# before coding. The pattern below is illustrative — actual SSE/HTTP protocol may differ.
# Check the README for authentication, request format, and response envelope.
async def get_champion_analysis(champion: str, role: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://mcp-api.op.gg/mcp",
            json={
                "tool": "lol_get_champion_analysis",
                "arguments": {"champion_name": champion, "position": role}
            }
        )
        return response.json()
```

Cache responses in-memory per (champion, role) key with 10-minute TTL to avoid hammering op.gg.

---

## Electron Main Process Changes

```typescript
// electron/main.ts additions

// Second window: Draft Window
function createDraftWindow(): BrowserWindow {
  return new BrowserWindow({
    width: 1200,
    height: 800,
    transparent: false,
    frame: true,
    alwaysOnTop: true,
    title: "RiftBuddy Draft",
    webPreferences: { contextIsolation: true, preload: ... }
  });
}

// New hotkeys
globalShortcut.register("CommandOrControl+Shift+D", () => {
  draftWin.show(); // toggle draft window
});
globalShortcut.register("CommandOrControl+Shift+Comma", () => {
  overlayWin.webContents.send("riftbuddy:settings-mode"); // 5s click-through off
});
// Tab hotkeys Cmd+Shift+1..5 sent to overlay window
```

---

## Riot Policy Compliance

- Draft Window uses only pre-game static data (champion stats, win rates, matchup guides). No live session-specific data from Riot servers.
- Champion picks entered manually by user — no champ-select API detection in v1.
- op.gg MCP returns aggregate statistics, not per-match live data.
- No augmentation of game UI directly (overlay is separate transparent window, not injected into League client).
- Compliant with Riot's "personal use / static data overlay" policy.

---

## Testing Plan

**Draft Window:**

- Mock op.gg MCP responses → verify recommendation panel renders top 5 correctly.
- Enter 10 champions → verify auto-transition to Screen 2.
- Test rune display with DDragon image URLs.
- Test "← 드래프트로 돌아가기" resets state.

**Post-game Coach:**

- Seed 5 fake GameState snapshots → call `/postgame/coach` → verify LLM JSON parses into 3 strengths, 3 improvements, 3 moments, 2 goals.
- Test "새 경기 시작" clears snapshots and navigates to Screen 1.

**Overlay tabs:**

- Inject fake event data → verify dragon timer counts down correctly.
- Verify gold tracker shows correct ally/enemy diff color.
- Verify click-through re-enables after 5s settings mode.

**Integration:**

- Full flow: app launch → draft → game start (overlay appears, draft minimizes) → game end (coach appears).
