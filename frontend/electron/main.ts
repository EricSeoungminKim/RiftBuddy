import { app, BrowserWindow, globalShortcut, ipcMain } from "electron";
import { exec } from "child_process";
import path from "path";
import {
  DraftContextPayload,
  draftContextFromChampSelectStatus,
  nextChampSelectVisibilityState,
} from "./champSelectTracking";

const isDev = process.env.NODE_ENV === "development";

let overlayWin: BrowserWindow | null = null;
let draftWin: BrowserWindow | null = null;
let leagueTrackInterval: ReturnType<typeof setInterval> | null = null;
let champSelectInterval: ReturnType<typeof setInterval> | null = null;
let wasInChampSelect = false;
let lastChampSelectDebugKey = "";
let lastDraftContext: DraftContextPayload | null = null;
const API_BASE = process.env.VITE_RIFTBUDDY_API_URL ?? "http://127.0.0.1:8001";

function logChampSelectState(inProgress: boolean, draftVisible: boolean): void {
  const key = `${inProgress}:${draftVisible}`;
  if (key === lastChampSelectDebugKey) return;
  lastChampSelectDebugKey = key;
  console.log(
    `RiftBuddy champ-select poll: inProgress=${inProgress} draftVisible=${draftVisible} api=${API_BASE}`,
  );
}

function createOverlayWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 520,
    height: 420,
    x: 1360,
    y: 90,
    type: "panel",
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    focusable: false,
    fullscreenable: false,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });
  win.setAlwaysOnTop(true, "screen-saver", 1);
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  win.setFocusable(false);
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
    width: 1240,
    height: 860,
    transparent: false,
    frame: true,
    alwaysOnTop: true,
    show: false,
    title: "RiftBuddy Draft",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });
  win.setAlwaysOnTop(true, "screen-saver", 1);
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  win.setFullScreenable(false);

  if (isDev) {
    win.loadURL("http://localhost:5173/src/draft/draft.html");
  } else {
    win.loadFile(path.join(__dirname, "src/draft/draft.html"));
  }

  win.on("close", (e) => {
    e.preventDefault();
    win.hide();
  });

  return win;
}

function getLeagueBoundsMac(): Promise<{
  x: number;
  y: number;
  width: number;
  height: number;
} | null> {
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

async function getLeagueBounds(): Promise<{
  x: number;
  y: number;
  width: number;
  height: number;
} | null> {
  if (process.platform === "darwin") {
    return getLeagueBoundsMac();
  }
  if (process.platform === "win32") {
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const getWindows = require("get-windows");
      const windows: Array<{
        title: string;
        bounds: { x: number; y: number; width: number; height: number };
      }> = await getWindows();
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
      const width = 520;
      const height = 420;
      win.setBounds({
        x: Math.max(bounds.x + 16, bounds.x + bounds.width - width - 28),
        y: bounds.y + 72,
        width,
        height,
      });
      win.setAlwaysOnTop(true, "screen-saver", 1);
      win.webContents.send("riftbuddy:league-bounds", bounds);
    }
  }, 2000);
}

function startChampSelectTracking(): void {
  const poll = async () => {
    try {
      const response = await fetch(`${API_BASE}/lcu/champ-select/status`);
      if (!response.ok) {
        console.log(`RiftBuddy champ-select poll failed: HTTP ${response.status}`);
        wasInChampSelect = false;
        return;
      }
      const data = await response.json();
      const draftVisible = Boolean(draftWin?.isVisible());
      const inProgress = Boolean(data?.inProgress);
      const previousWasInChampSelect = wasInChampSelect;
      logChampSelectState(inProgress, draftVisible);
      if (inProgress) {
        lastDraftContext = draftContextFromChampSelectStatus(data) ?? lastDraftContext;
      } else if (previousWasInChampSelect && lastDraftContext) {
        void sendDraftContext(lastDraftContext);
        lastDraftContext = null;
      }
      const nextState = nextChampSelectVisibilityState(
        inProgress,
        wasInChampSelect,
        draftVisible,
      );
      wasInChampSelect = nextState.wasInChampSelect;
      if (nextState.shouldShowDraft) {
        console.log("RiftBuddy Draft auto-open: champion select detected");
        draftWin?.setAlwaysOnTop(true, "screen-saver", 1);
        app.focus({ steal: true });
        draftWin?.showInactive();
        draftWin?.show();
        draftWin?.moveTop();
        draftWin?.focus();
      }
    } catch (error) {
      console.log(`RiftBuddy champ-select poll error: ${error instanceof Error ? error.message : String(error)}`);
      wasInChampSelect = false;
    }
  };
  void poll();
  champSelectInterval = setInterval(poll, 2500);
}

async function sendDraftContext(context: DraftContextPayload): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/game/draft-context`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(context),
    });
    if (!response.ok) {
      console.log(`RiftBuddy draft context send failed: HTTP ${response.status}`);
    }
  } catch (error) {
    console.log(`RiftBuddy draft context send error: ${error instanceof Error ? error.message : String(error)}`);
  }
}

function showPostGameWindow(): void {
  draftWin?.setAlwaysOnTop(true, "screen-saver", 1);
  app.focus({ steal: true });
  draftWin?.showInactive();
  draftWin?.show();
  draftWin?.moveTop();
  draftWin?.focus();
}

app.whenReady().then(() => {
  overlayWin = createOverlayWindow();
  draftWin = createDraftWindow();

  startLeagueTracking(overlayWin);
  startChampSelectTracking();

  // Cmd+Shift+B — 현재 게임 상황 기반 조언 (이벤트 + RAG)
  globalShortcut.register("CommandOrControl+Shift+B", () => {
    overlayWin?.webContents.send("riftbuddy:request-advice");
  });
  // Cmd+Shift+C — 상대 챔피언 매치업 + OP.GG 통계
  globalShortcut.register("CommandOrControl+Shift+C", () => {
    overlayWin?.webContents.send("riftbuddy:request-matchup");
  });
  // Cmd+Shift+1 — 아이템 추천
  globalShortcut.register("CommandOrControl+Shift+1", () => {
    overlayWin?.webContents.send("riftbuddy:request-items");
  });
  // Cmd+Shift+2 — 매크로 / 오브젝트 타이밍
  globalShortcut.register("CommandOrControl+Shift+2", () => {
    overlayWin?.webContents.send("riftbuddy:request-macro");
  });
  globalShortcut.register("CommandOrControl+Shift+L", () => {
    overlayWin?.webContents.send("riftbuddy:toggle-language");
  });
  globalShortcut.register("CommandOrControl+Shift+D", () => {
    if (draftWin?.isVisible()) {
      draftWin.hide();
    } else {
      draftWin?.setAlwaysOnTop(true, "screen-saver", 1);
      app.focus({ steal: true });
      draftWin?.showInactive();
      draftWin?.show();
      draftWin?.moveTop();
      draftWin?.focus();
    }
  });

  ipcMain.on("riftbuddy:show-postgame-window", () => {
    showPostGameWindow();
  });
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
  if (leagueTrackInterval) clearInterval(leagueTrackInterval);
  if (champSelectInterval) clearInterval(champSelectInterval);
});
app.on("window-all-closed", () => app.quit());
