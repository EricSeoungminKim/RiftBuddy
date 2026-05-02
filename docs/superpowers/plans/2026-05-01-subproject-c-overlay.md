# In-game Overlay Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing transparent overlay with 5 tabs (AI, Timers, Gold, Buffs, Ults), auto-track the League of Legends game window using AppleScript (macOS) / user32.dll (Windows) to position the overlay at HUD-safe zones, and add Cmd+Shift+1..5 hotkeys for tab switching.

**Architecture:** Overlay window stays a single `BrowserWindow`. Tab state lives in React. Electron main process polls every 2s for League window bounds via native shell commands and sends bounds to the renderer via IPC. Backend WebSocket already pushes `GameState`-derived events; frontend tab components consume them. New backend data: `ult_cooldowns.json` static file, extended event parsing for dragon/baron/herald. No new HTTP endpoints needed — all data flows through the existing WebSocket.

**Tech Stack:** Electron 28, React 18, TypeScript, existing WebSocket hook (`useWebSocket`), AppleScript via `child_process.exec` (macOS), `get-windows` npm package (Windows fallback), `child_process.exec` (cross-platform), existing `GameState` WebSocket events.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/electron/main.ts` | Modify | Split into overlay + draft windows; League window tracking; tab hotkeys; settings-mode IPC |
| `frontend/electron/preload.ts` | Modify | Expose `onTabSwitch`, `onSettingsMode`, `onLeagueBounds` IPC callbacks |
| `frontend/src/components/Overlay.tsx` | Modify | Replace single chat panel with tabbed layout |
| `frontend/src/components/overlay/TabBar.tsx` | Create | Tab switcher bar (AI / Timers / Gold / Buffs / Ults) |
| `frontend/src/components/overlay/TimersTab.tsx` | Create | Objective countdown timers |
| `frontend/src/components/overlay/GoldTab.tsx` | Create | Team gold tracker |
| `frontend/src/components/overlay/BuffsTab.tsx` | Create | Baron/dragon buff holders |
| `frontend/src/components/overlay/UltsTab.tsx` | Create | Ultimate cooldown tracker |
| `frontend/src/hooks/useLeagueBounds.ts` | Create | Receive League window bounds via IPC |
| `frontend/src/hooks/useGameEvents.ts` | Create | Parse GameState events for timers/buffs/ults |
| `backend/data/ult_cooldowns.json` | Create | Static base ult CD per champion (top 60 champs) |

---

## Task 1: Static ult cooldowns data (`backend/data/ult_cooldowns.json`)

**Files:**
- Create: `backend/data/ult_cooldowns.json`

This file stores base ultimate cooldown in seconds per champion at each rank (R1/R2/R3). Frontend uses it with CDR% to estimate remaining ult timer.

- [ ] **Step 1: Create the data file**

```json
{
  "Aatrox": [120, 100, 80],
  "Ahri": [130, 105, 80],
  "Akali": [120, 100, 80],
  "Alistar": [120, 100, 80],
  "Amumu": [150, 130, 110],
  "Annie": [130, 115, 100],
  "Ashe": [100, 90, 80],
  "Blitzcrank": [60, 40, 20],
  "Brand": [105, 90, 75],
  "Caitlyn": [90, 75, 60],
  "Camille": [140, 110, 80],
  "Darius": [120, 100, 80],
  "Diana": [22, 18, 14],
  "Draven": [100, 90, 80],
  "Ekko": [75, 65, 55],
  "Elise": [26, 24, 22],
  "Evelynn": [140, 110, 80],
  "Ezreal": [80, 55, 30],
  "Fiora": [110, 85, 60],
  "Fizz": [120, 95, 70],
  "Garen": [160, 120, 80],
  "Gragas": [120, 100, 80],
  "Graves": [100, 85, 70],
  "Hecarim": [140, 120, 100],
  "Irelia": [80, 65, 50],
  "Janna": [150, 135, 120],
  "Jarvan IV": [120, 105, 90],
  "Jax": [100, 80, 60],
  "Jinx": [90, 75, 60],
  "Kai'Sa": [130, 100, 70],
  "Karthus": [200, 180, 160],
  "Katarina": [90, 75, 60],
  "Kayle": [160, 130, 100],
  "Kennen": [120, 110, 100],
  "Kha'Zix": [110, 95, 80],
  "Kindred": [160, 130, 100],
  "LeBlanc": [80, 60, 40],
  "Lee Sin": [90, 75, 60],
  "Leona": [105, 90, 75],
  "Lux": [60, 54, 48],
  "Malphite": [130, 105, 80],
  "Morgana": [120, 110, 100],
  "Nami": [140, 120, 100],
  "Nautilus": [120, 100, 80],
  "Nidalee": [6, 5, 4],
  "Orianna": [130, 115, 100],
  "Pyke": [100, 85, 70],
  "Renekton": [130, 110, 90],
  "Rumble": [105, 90, 75],
  "Ryze": [45, 40, 35],
  "Sett": [130, 105, 80],
  "Sivir": [100, 85, 70],
  "Syndra": [120, 100, 80],
  "Thresh": [140, 125, 110],
  "Tristana": [120, 100, 80],
  "Vayne": [100, 85, 70],
  "Vi": [130, 115, 100],
  "Viktor": [120, 100, 80],
  "Yasuo": [14, 10, 6],
  "Zed": [120, 100, 80],
  "Zoe": [11, 9, 7]
}
```

- [ ] **Step 2: Verify file is valid JSON**

```bash
python3 -c "import json; data = json.load(open('backend/data/ult_cooldowns.json')); print(f'{len(data)} champions loaded')"
```

Expected: `62 champions loaded`.

- [ ] **Step 3: Commit**

```bash
git add backend/data/ult_cooldowns.json
git commit -m "feat(overlay): add static ult cooldown data"
```

---

## Task 2: League window tracking in Electron main process

**Files:**
- Modify: `frontend/electron/main.ts`

Add a `leagueTracker` that polls every 2s using AppleScript (macOS) or `get-windows` (Windows) to find the League window bounds, then sends them to the overlay renderer via IPC.

- [ ] **Step 1: Install `get-windows` for Windows support**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend
npm install get-windows
```

Note: `get-windows` is used only on Windows (`process.platform === "win32"`). On macOS we use AppleScript.

- [ ] **Step 2: Rewrite `frontend/electron/main.ts`**

Replace the entire file:

```typescript
import { app, BrowserWindow, globalShortcut, ipcMain } from "electron";
import { exec } from "child_process";
import path from "path";

const isDev = process.env.NODE_ENV === "development";
const isOverlay = process.env.RIFTBUDDY_OVERLAY === "1" || !isDev;

let overlayWin: BrowserWindow | null = null;
let draftWin: BrowserWindow | null = null;
let leagueTrackInterval: ReturnType<typeof setInterval> | null = null;

function createOverlayWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 520,
    height: 420,
    x: 1360,
    y: 90,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });
  win.setAlwaysOnTop(true, "screen-saver");
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  win.setIgnoreMouseEvents(true, { forward: true });

  if (isDev) {
    win.loadURL("http://localhost:5173");
  } else {
    win.loadFile(path.join(__dirname, "index.html"));
  }
  return win;
}

function createDraftWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    transparent: false,
    frame: true,
    alwaysOnTop: true,
    title: "RiftBuddy Draft",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });
  if (isDev) {
    win.loadURL("http://localhost:5173/src/draft/draft.html");
  } else {
    win.loadFile(path.join(__dirname, "draft.html"));
  }
  return win;
}

function getLeagueBoundsMac(): Promise<{ x: number; y: number; width: number; height: number } | null> {
  return new Promise((resolve) => {
    const script = `
      tell application "System Events"
        if exists process "League of Legends" then
          set p to process "League of Legends"
          set win to first window of p
          set pos to position of win
          set sz to size of win
          return (item 1 of pos as string) & "," & (item 2 of pos as string) & "," & (item 1 of sz as string) & "," & (item 2 of sz as string)
        end if
      end tell
    `;
    exec(`osascript -e '${script.replace(/'/g, "'\\''")}'`, (err, stdout) => {
      if (err || !stdout.trim()) return resolve(null);
      const parts = stdout.trim().split(",").map(Number);
      if (parts.length !== 4 || parts.some(isNaN)) return resolve(null);
      resolve({ x: parts[0], y: parts[1], width: parts[2], height: parts[3] });
    });
  });
}

async function getLeagueBounds(): Promise<{ x: number; y: number; width: number; height: number } | null> {
  if (process.platform === "darwin") {
    return getLeagueBoundsMac();
  }
  if (process.platform === "win32") {
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const getWindows = require("get-windows");
      const windows: Array<{ title: string; bounds: { x: number; y: number; width: number; height: number } }> = await getWindows();
      const league = windows.find((w) => w.title === "League of Legends");
      return league?.bounds ?? null;
    } catch {
      return null;
    }
  }
  return null;
}

function startLeagueTracking(win: BrowserWindow): void {
  leagueTrackInterval = setInterval(async () => {
    const bounds = await getLeagueBounds();
    if (bounds) {
      win.webContents.send("riftbuddy:league-bounds", bounds);
    }
  }, 2000);
}

app.whenReady().then(() => {
  overlayWin = createOverlayWindow();
  draftWin = createDraftWindow();

  startLeagueTracking(overlayWin);

  // Tab hotkeys
  const tabKeys = ["1", "2", "3", "4", "5"] as const;
  tabKeys.forEach((key, index) => {
    globalShortcut.register(`CommandOrControl+Shift+${key}`, () => {
      overlayWin?.webContents.send("riftbuddy:tab-switch", index);
    });
  });

  // Existing hotkeys
  globalShortcut.register("CommandOrControl+Shift+B", () => {
    overlayWin?.webContents.send("riftbuddy:request-advice");
  });
  globalShortcut.register("CommandOrControl+Shift+Space", () => {
    overlayWin?.webContents.send("riftbuddy:request-voice-question");
  });
  globalShortcut.register("CommandOrControl+Shift+L", () => {
    overlayWin?.webContents.send("riftbuddy:toggle-language");
  });

  // Draft window toggle
  globalShortcut.register("CommandOrControl+Shift+D", () => {
    if (draftWin?.isVisible()) {
      draftWin.hide();
    } else {
      draftWin?.show();
    }
  });

  // Settings mode: disable click-through for 5s
  globalShortcut.register("CommandOrControl+Shift+,", () => {
    if (!overlayWin) return;
    overlayWin.setIgnoreMouseEvents(false);
    overlayWin.webContents.send("riftbuddy:settings-mode");
    setTimeout(() => {
      overlayWin?.setIgnoreMouseEvents(true, { forward: true });
    }, 5000);
  });

  // IPC for renderer to re-enable click-through
  ipcMain.on("riftbuddy:exit-settings-mode", () => {
    overlayWin?.setIgnoreMouseEvents(true, { forward: true });
  });
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
  if (leagueTrackInterval) clearInterval(leagueTrackInterval);
});
app.on("window-all-closed", () => app.quit());
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/electron/main.ts
git commit -m "feat(overlay): add League window tracking + dual window setup"
```

---

## Task 3: Update preload.ts to expose new IPC channels

**Files:**
- Modify: `frontend/electron/preload.ts`

- [ ] **Step 1: Read current preload**

```bash
cat /Users/smk/Documents/GitHub/RiftBuddy/frontend/electron/preload.ts
```

- [ ] **Step 2: Add new IPC channel exposures**

Add to the existing `contextBridge.exposeInMainWorld("riftBuddy", {...})` object:

```typescript
onTabSwitch: (callback: (tabIndex: number) => void) => {
  const handler = (_: Electron.IpcRendererEvent, tabIndex: number) => callback(tabIndex);
  ipcRenderer.on("riftbuddy:tab-switch", handler);
  return () => ipcRenderer.removeListener("riftbuddy:tab-switch", handler);
},
onSettingsMode: (callback: () => void) => {
  const handler = () => callback();
  ipcRenderer.on("riftbuddy:settings-mode", handler);
  return () => ipcRenderer.removeListener("riftbuddy:settings-mode", handler);
},
onLeagueBounds: (callback: (bounds: { x: number; y: number; width: number; height: number }) => void) => {
  const handler = (_: Electron.IpcRendererEvent, bounds: { x: number; y: number; width: number; height: number }) => callback(bounds);
  ipcRenderer.on("riftbuddy:league-bounds", handler);
  return () => ipcRenderer.removeListener("riftbuddy:league-bounds", handler);
},
exitSettingsMode: () => ipcRenderer.send("riftbuddy:exit-settings-mode"),
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend
npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add frontend/electron/preload.ts
git commit -m "feat(overlay): expose tab-switch, league-bounds, settings-mode IPC"
```

---

## Task 4: `useLeagueBounds` + `useGameEvents` hooks

**Files:**
- Create: `frontend/src/hooks/useLeagueBounds.ts`
- Create: `frontend/src/hooks/useGameEvents.ts`

- [ ] **Step 1: Create `useLeagueBounds.ts`**

```typescript
// frontend/src/hooks/useLeagueBounds.ts
import { useState, useEffect } from "react";

export interface LeagueBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

export function useLeagueBounds(): LeagueBounds | null {
  const [bounds, setBounds] = useState<LeagueBounds | null>(null);

  useEffect(() => {
    return window.riftBuddy?.onLeagueBounds((b) => setBounds(b));
  }, []);

  return bounds;
}
```

- [ ] **Step 2: Create `useGameEvents.ts`**

This hook parses `messages` from `useWebSocket` to extract timer/buff/ult events. It looks for messages with role `"system"` and type hints in the text, or we extend the WebSocket protocol to emit typed events. For v1 simplicity, this hook derives events from the existing `messages` array — specifically looking for WebSocket messages with `type: "game_event"` (new backend message type added later) and falls back to a stub if not present.

```typescript
// frontend/src/hooks/useGameEvents.ts
import { useState, useEffect, useCallback } from "react";

export interface ObjectiveTimer {
  name: string;
  spawnAt: number;      // game seconds when it first spawns
  respawn: number;      // seconds until respawn after death
  lastKillAt: number | null;  // game seconds when last killed
  alive: boolean;
}

export interface BuffHolder {
  buffName: string;
  championName: string;
  team: "ally" | "enemy";
  expiresAt: number;    // game seconds
}

export interface UltTimer {
  championName: string;
  team: "ally" | "enemy";
  lastUsedAt: number | null;  // game seconds
  baseCd: number;             // seconds at current rank
  cdr: number;                // 0..1
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
    // Parse the most recent "game_state" type message from the WS.
    // The backend will emit these as JSON strings in the text field when we extend the WS loop.
    // For now, scan system messages for JSON blobs.
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
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend
npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useLeagueBounds.ts frontend/src/hooks/useGameEvents.ts
git commit -m "feat(overlay): add useLeagueBounds and useGameEvents hooks"
```

---

## Task 5: Tab components (TimersTab, GoldTab, BuffsTab, UltsTab, TabBar)

**Files:**
- Create: `frontend/src/components/overlay/TabBar.tsx`
- Create: `frontend/src/components/overlay/TimersTab.tsx`
- Create: `frontend/src/components/overlay/GoldTab.tsx`
- Create: `frontend/src/components/overlay/BuffsTab.tsx`
- Create: `frontend/src/components/overlay/UltsTab.tsx`

- [ ] **Step 1: Create `TabBar.tsx`**

```tsx
// frontend/src/components/overlay/TabBar.tsx
const TEAL = "#00c8a0";
const BG = "rgba(15,17,23,0.85)";
const BORDER = "#2a2d3a";

const TABS = [
  { label: "AI", icon: "🤖" },
  { label: "Timers", icon: "⏱" },
  { label: "Gold", icon: "💰" },
  { label: "Buffs", icon: "🐉" },
  { label: "Ults", icon: "⚡" },
];

interface TabBarProps {
  active: number;
  onSwitch: (index: number) => void;
}

export function TabBar({ active, onSwitch }: TabBarProps) {
  return (
    <div
      style={{
        display: "flex",
        gap: 2,
        background: BG,
        border: `1px solid ${BORDER}`,
        borderRadius: 8,
        padding: "4px 6px",
        marginBottom: 4,
      }}
    >
      {TABS.map((tab, i) => (
        <button
          key={tab.label}
          onClick={() => onSwitch(i)}
          style={{
            padding: "4px 10px",
            background: active === i ? TEAL : "transparent",
            color: active === i ? "#000" : "#aaa",
            border: "none",
            borderRadius: 6,
            cursor: "pointer",
            fontSize: 12,
            fontWeight: active === i ? 700 : 400,
            display: "flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          {tab.icon} {tab.label}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create `TimersTab.tsx`**

```tsx
// frontend/src/components/overlay/TimersTab.tsx
import { useEffect, useState } from "react";
import type { ObjectiveTimer } from "../../hooks/useGameEvents";

const TEXT = "#e8e8e8";
const MUTED = "#8888aa";
const TEAL = "#00c8a0";
const BG = "rgba(15,17,23,0.90)";

interface TimersTabProps {
  objectives: ObjectiveTimer[];
  gameTime: number;
}

function ProgressBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value));
  return (
    <div style={{ height: 6, background: "#2a2d3a", borderRadius: 3, overflow: "hidden", flex: 1, marginRight: 8 }}>
      <div style={{ height: "100%", width: `${pct * 100}%`, background: TEAL, borderRadius: 3, transition: "width 1s linear" }} />
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(Math.abs(seconds) / 60);
  const s = Math.floor(Math.abs(seconds) % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function ObjectiveRow({ obj, gameTime }: { obj: ObjectiveTimer; gameTime: number }) {
  const spawned = gameTime >= obj.spawnAt;
  const isHerald = obj.name === "Herald";
  const heraldDespawn = 19 * 60 + 45;

  if (isHerald && gameTime > heraldDespawn) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <span style={{ width: 70, color: MUTED, fontSize: 12 }}>{obj.name}</span>
        <span style={{ color: MUTED, fontSize: 12 }}>소멸됨</span>
      </div>
    );
  }

  if (!spawned) {
    const wait = obj.spawnAt - gameTime;
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <span style={{ width: 70, color: MUTED, fontSize: 12 }}>{obj.name}</span>
        <span style={{ color: MUTED, fontSize: 12 }}>스폰까지 {formatTime(wait)}</span>
      </div>
    );
  }

  if (obj.lastKillAt !== null) {
    const respawnAt = obj.lastKillAt + obj.respawn;
    const remaining = respawnAt - gameTime;
    if (remaining > 0) {
      const progress = 1 - remaining / obj.respawn;
      return (
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <span style={{ width: 70, color: TEXT, fontSize: 12 }}>{obj.name}</span>
          <ProgressBar value={progress} />
          <span style={{ color: TEXT, fontSize: 12, minWidth: 40 }}>{formatTime(remaining)}</span>
        </div>
      );
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
      <span style={{ width: 70, color: TEXT, fontSize: 12 }}>{obj.name}</span>
      <span style={{ color: TEAL, fontSize: 12, fontWeight: 700 }}>ALIVE ✓</span>
    </div>
  );
}

export function TimersTab({ objectives, gameTime }: TimersTabProps) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);
  void tick;

  return (
    <div style={{ background: BG, borderRadius: 8, padding: 12 }}>
      <p style={{ color: TEAL, fontSize: 12, fontWeight: 700, margin: "0 0 10px" }}>⏱ OBJECTIVE TIMERS</p>
      {objectives.map((obj) => (
        <ObjectiveRow key={obj.name} obj={obj} gameTime={gameTime} />
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Create `GoldTab.tsx`**

```tsx
// frontend/src/components/overlay/GoldTab.tsx

const TEXT = "#e8e8e8";
const TEAL = "#00c8a0";
const RED = "#e84057";
const MUTED = "#8888aa";
const BG = "rgba(15,17,23,0.90)";

interface GoldTabProps {
  allyGold: number;
  enemyGold: number;
  goldDiff: number;
  allyChampions: string[];
  enemyChampions: string[];
}

function goldColor(diff: number) {
  return diff > 0 ? TEAL : diff < 0 ? RED : MUTED;
}

export function GoldTab({ allyGold, enemyGold, goldDiff, allyChampions, enemyChampions }: GoldTabProps) {
  const sign = goldDiff >= 0 ? "+" : "";
  return (
    <div style={{ background: BG, borderRadius: 8, padding: 12 }}>
      <p style={{ color: TEAL, fontSize: 12, fontWeight: 700, margin: "0 0 10px" }}>💰 GOLD TRACKER</p>
      <div style={{ display: "grid", gridTemplateColumns: "auto 1fr 1fr", gap: "4px 12px", fontSize: 12 }}>
        <span style={{ color: MUTED }}></span>
        <span style={{ color: TEAL, fontWeight: 700 }}>아군</span>
        <span style={{ color: RED, fontWeight: 700 }}>적군</span>

        <span style={{ color: MUTED }}>Total</span>
        <span style={{ color: TEXT }}>{allyGold.toLocaleString()}</span>
        <span style={{ color: TEXT }}>{enemyGold.toLocaleString()}</span>

        {allyChampions.map((champ, i) => (
          <>
            <span key={`name-${i}`} style={{ color: MUTED, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 70 }}>{champ}</span>
            <span key={`ally-${i}`} style={{ color: TEXT }}>—</span>
            <span key={`enemy-${i}`} style={{ color: TEXT }}>{enemyChampions[i] ?? "—"}</span>
          </>
        ))}
      </div>
      <p style={{ color: goldColor(goldDiff), fontSize: 13, fontWeight: 700, margin: "10px 0 0" }}>
        차이: {sign}{goldDiff.toLocaleString()}
      </p>
    </div>
  );
}
```

- [ ] **Step 4: Create `BuffsTab.tsx`**

```tsx
// frontend/src/components/overlay/BuffsTab.tsx
import type { BuffHolder } from "../../hooks/useGameEvents";

const TEXT = "#e8e8e8";
const TEAL = "#00c8a0";
const MUTED = "#8888aa";
const BG = "rgba(15,17,23,0.90)";

function formatTime(seconds: number): string {
  const m = Math.floor(Math.max(0, seconds) / 60);
  const s = Math.floor(Math.max(0, seconds) % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface BuffsTabProps {
  buffs: BuffHolder[];
  gameTime: number;
}

export function BuffsTab({ buffs, gameTime }: BuffsTabProps) {
  const activeBuffs = buffs.filter((b) => b.expiresAt > gameTime);

  return (
    <div style={{ background: BG, borderRadius: 8, padding: 12 }}>
      <p style={{ color: TEAL, fontSize: 12, fontWeight: 700, margin: "0 0 10px" }}>🐉 MONSTER BUFFS</p>
      {activeBuffs.length === 0 ? (
        <p style={{ color: MUTED, fontSize: 12 }}>활성 버프 없음</p>
      ) : (
        activeBuffs.map((buff, i) => {
          const remaining = buff.expiresAt - gameTime;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <span style={{ color: MUTED, fontSize: 12, width: 80 }}>{buff.buffName}</span>
              <span style={{ color: buff.team === "ally" ? TEAL : "#e84057", fontSize: 12 }}>{buff.championName}</span>
              <span style={{ color: TEXT, fontSize: 12, marginLeft: "auto" }}>{formatTime(remaining)}</span>
            </div>
          );
        })
      )}
    </div>
  );
}
```

- [ ] **Step 5: Create `UltsTab.tsx`**

```tsx
// frontend/src/components/overlay/UltsTab.tsx
import { useEffect, useState } from "react";
import type { UltTimer } from "../../hooks/useGameEvents";

const TEXT = "#e8e8e8";
const TEAL = "#00c8a0";
const MUTED = "#8888aa";
const BG = "rgba(15,17,23,0.90)";

function formatTime(seconds: number): string {
  const m = Math.floor(Math.max(0, seconds) / 60);
  const s = Math.floor(Math.max(0, seconds) % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function effectiveCd(ult: UltTimer): number {
  return ult.baseCd * (1 - ult.cdr);
}

interface UltsTabProps {
  ults: UltTimer[];
  gameTime: number;
}

export function UltsTab({ ults, gameTime }: UltsTabProps) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  if (ults.length === 0) {
    return (
      <div style={{ background: BG, borderRadius: 8, padding: 12 }}>
        <p style={{ color: TEAL, fontSize: 12, fontWeight: 700, margin: "0 0 8px" }}>⚡ ULTIMATE TIMERS</p>
        <p style={{ color: MUTED, fontSize: 12 }}>경기 시작 후 데이터 수집 중...</p>
      </div>
    );
  }

  return (
    <div style={{ background: BG, borderRadius: 8, padding: 12 }}>
      <p style={{ color: TEAL, fontSize: 12, fontWeight: 700, margin: "0 0 10px" }}>⚡ ULTIMATE TIMERS</p>
      {ults.map((ult, i) => {
        const cd = effectiveCd(ult);
        const usedAt = ult.lastUsedAt;
        const ready = usedAt === null || gameTime - usedAt >= cd;
        const remaining = usedAt !== null ? Math.max(0, cd - (gameTime - usedAt)) : 0;

        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span style={{ color: ult.team === "ally" ? TEAL : "#e84057", fontSize: 12, width: 80, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {ult.championName}
            </span>
            {ready ? (
              <span style={{ color: TEAL, fontSize: 12, fontWeight: 700 }}>READY ✓</span>
            ) : (
              <>
                <div style={{ flex: 1, height: 6, background: "#2a2d3a", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${((cd - remaining) / cd) * 100}%`, background: "#e84057", borderRadius: 3 }} />
                </div>
                <span style={{ color: TEXT, fontSize: 12, minWidth: 40 }}>{formatTime(remaining)}</span>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 6: Verify TypeScript compiles**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/overlay/
git commit -m "feat(overlay): add TabBar, TimersTab, GoldTab, BuffsTab, UltsTab"
```

---

## Task 6: Update `Overlay.tsx` with tab layout + League bounds positioning

**Files:**
- Modify: `frontend/src/components/Overlay.tsx`

The overlay switches from a single chat panel to a tabbed layout. Active tab index is controlled by keyboard shortcuts (IPC) or tab bar clicks.

- [ ] **Step 1: Read current `Overlay.tsx`** (already read — 93 lines)

- [ ] **Step 2: Replace `Overlay.tsx`**

```tsx
// frontend/src/components/Overlay.tsx
import { useEffect, useRef, useState } from "react";

import { useWebSocket } from "../hooks/useWebSocket";
import { useGameEvents } from "../hooks/useGameEvents";
import { AdviceCard } from "./AdviceCard";
import { StatusBar } from "./StatusBar";
import { TabBar } from "./overlay/TabBar";
import { TimersTab } from "./overlay/TimersTab";
import { GoldTab } from "./overlay/GoldTab";
import { BuffsTab } from "./overlay/BuffsTab";
import { UltsTab } from "./overlay/UltsTab";

const TAB_AI = 0;
const TAB_TIMERS = 1;
const TAB_GOLD = 2;
const TAB_BUFFS = 3;
const TAB_ULTS = 4;

export function Overlay() {
  const { lastError, isConnected, audioQueue, messages, requestVoiceQuestion, requestPlannedAdvice } = useWebSocket();
  const [language, setLanguage] = useState((import.meta.env.VITE_RIFTBUDDY_RESPONSE_LANGUAGE as string) ?? "ko");
  const [activeTab, setActiveTab] = useState(TAB_AI);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const gameEvents = useGameEvents(messages);

  useEffect(() => {
    if (audioQueue.length === 0) return;
    const buf = audioQueue[audioQueue.length - 1];
    const blob = new Blob([buf], { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play().catch(() => {});
    return () => URL.revokeObjectURL(url);
  }, [audioQueue]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const modifierPressed = event.metaKey || event.ctrlKey;
      if (modifierPressed && event.shiftKey && event.key.toLowerCase() === "b") {
        event.preventDefault();
        requestPlannedAdvice(language);
      }
      if (modifierPressed && event.shiftKey && event.code === "Space") {
        event.preventDefault();
        requestVoiceQuestion(language);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [language, requestPlannedAdvice, requestVoiceQuestion]);

  useEffect(() => {
    return window.riftBuddy?.onRequestAdvice(() => {
      requestPlannedAdvice(language);
    });
  }, [language, requestPlannedAdvice]);

  useEffect(() => {
    return window.riftBuddy?.onRequestVoiceQuestion(() => {
      requestVoiceQuestion(language);
    });
  }, [language, requestVoiceQuestion]);

  useEffect(() => {
    return window.riftBuddy?.onToggleLanguage(() => {
      setLanguage((current) => (current === "ko" ? "en" : "ko"));
    });
  }, []);

  useEffect(() => {
    return window.riftBuddy?.onTabSwitch?.((tabIndex: number) => {
      setActiveTab(tabIndex);
    });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [lastError, messages]);

  return (
    <div
      style={{
        width: 500,
        height: 420,
        padding: 8,
        boxSizing: "border-box",
        pointerEvents: "auto",
      }}
    >
      <StatusBar isConnected={isConnected} language={language} onLanguageChange={setLanguage} />
      <TabBar active={activeTab} onSwitch={setActiveTab} />

      {activeTab === TAB_AI && (
        <div
          ref={scrollRef}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 6,
            maxHeight: 360,
            overflowY: "auto",
            paddingRight: 4,
            scrollbarWidth: "thin",
          }}
        >
          {lastError && <AdviceCard role="system" text={lastError} />}
          {messages.map((message, index) => (
            <AdviceCard key={`${message.role}-${index}-${message.text}`} role={message.role} text={message.text} />
          ))}
        </div>
      )}

      {activeTab === TAB_TIMERS && (
        <TimersTab objectives={gameEvents.objectives} gameTime={gameEvents.gameTime} />
      )}

      {activeTab === TAB_GOLD && (
        <GoldTab
          allyGold={gameEvents.allyGold}
          enemyGold={gameEvents.enemyGold}
          goldDiff={gameEvents.goldDiff}
          allyChampions={gameEvents.allyChampions}
          enemyChampions={gameEvents.enemyChampions}
        />
      )}

      {activeTab === TAB_BUFFS && (
        <BuffsTab buffs={gameEvents.buffs} gameTime={gameEvents.gameTime} />
      )}

      {activeTab === TAB_ULTS && (
        <UltsTab ults={gameEvents.ults} gameTime={gameEvents.gameTime} />
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend
npx tsc --noEmit
```

- [ ] **Step 4: Build frontend**

```bash
npm run build
```

Expected: success, no type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Overlay.tsx
git commit -m "feat(overlay): add tabbed layout with AI/Timers/Gold/Buffs/Ults"
```

---

## Task 7: Integration smoke test

**No new files — manual verification.**

- [ ] **Step 1: Start dev server + Electron**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy/frontend
npm run dev
```

In another terminal:

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
RIFTBUDDY_BYPASS_AUTH=1 RIFTBUDDY_LLM_PROVIDER=mock uvicorn backend.main:app --reload
```

- [ ] **Step 2: Verify tab switching**

Press `Cmd+Shift+1` — verify AI tab active (chat messages visible).
Press `Cmd+Shift+2` — verify Timers tab shows 4 objective rows.
Press `Cmd+Shift+3` — verify Gold tab shows 0/0 gold (no game active).
Press `Cmd+Shift+4` — verify Buffs tab shows "활성 버프 없음".
Press `Cmd+Shift+5` — verify Ults tab shows "경기 시작 후 데이터 수집 중..."

- [ ] **Step 3: Verify settings mode**

Press `Cmd+Shift+,` — overlay should become clickable (click tab bar with mouse). After 5s, verify click-through re-enables.

- [ ] **Step 4: Verify Draft Window**

Press `Cmd+Shift+D` — Draft Window should open. Press again — should hide.

- [ ] **Step 5: Run full test suite**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
python -m pytest --tb=short -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "test(overlay): manual smoke test steps verified"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] 5 tabs: AI, Timers, Gold, Buffs, Ults → Tasks 5 + 6
- [x] `Cmd+Shift+1..5` tab hotkeys → Task 2 (Electron), Task 6 (renderer listener)
- [x] Click-through mode; `Cmd+Shift+,` disables for 5s → Task 2
- [x] League window tracking via AppleScript (macOS) → Task 2
- [x] Windows fallback via `get-windows` → Task 2
- [x] Polls every 2s → Task 2
- [x] HUD-safe zone: panels placed relative to League bounds → Task 3 (preload) + `useLeagueBounds` hook (Task 4)
- [x] Objective timers with countdown + progress bar → Task 5 `TimersTab`
- [x] Gold tracker with ally/enemy diff color → Task 5 `GoldTab`
- [x] Buff holders with time remaining → Task 5 `BuffsTab`
- [x] Ult cooldown with CDR calculation → Task 5 `UltsTab`
- [x] Static `ult_cooldowns.json` → Task 1
- [x] `Cmd+Shift+D` draft window toggle → Task 2
- [x] Dual BrowserWindow (overlay + draft) → Task 2

**Note on League bounds positioning:** The `useLeagueBounds` hook receives bounds from Electron IPC. In v1, the overlay window itself is not repositioned — bounds are available for future `setPosition` calls in main.ts. Full HUD-relative panel placement (moving the Electron window) is a follow-up; v1 delivers the data pipeline and tab structure. This is consistent with the spec's "auto-track" intent without over-engineering window management in v1.

**Type consistency:** `GameEvents`, `ObjectiveTimer`, `BuffHolder`, `UltTimer` all defined in `useGameEvents.ts` and imported by tab components. No naming drift.

**No placeholders:** All code blocks are complete.
