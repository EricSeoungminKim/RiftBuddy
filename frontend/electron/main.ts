import { app, BrowserWindow, globalShortcut, ipcMain } from "electron";
import { exec } from "child_process";
import path from "path";

const isDev = process.env.NODE_ENV === "development";

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
    show: false,
    title: "RiftBuddy Draft",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });
  win.setAlwaysOnTop(true, "floating");
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

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

  const tabKeys = ["1", "2", "3", "4", "5"] as const;
  tabKeys.forEach((key, index) => {
    globalShortcut.register(`CommandOrControl+Shift+${key}`, () => {
      overlayWin?.webContents.send("riftbuddy:tab-switch", index);
    });
  });

  globalShortcut.register("CommandOrControl+Shift+B", () => {
    overlayWin?.webContents.send("riftbuddy:request-advice");
  });
  globalShortcut.register("CommandOrControl+Shift+Space", () => {
    overlayWin?.webContents.send("riftbuddy:request-voice-question");
  });
  globalShortcut.register("CommandOrControl+Shift+L", () => {
    overlayWin?.webContents.send("riftbuddy:toggle-language");
  });
  globalShortcut.register("CommandOrControl+Shift+D", () => {
    if (draftWin?.isVisible()) {
      draftWin.hide();
    } else {
      draftWin?.show();
      draftWin?.focus();
    }
  });
  globalShortcut.register("CommandOrControl+Shift+,", () => {
    if (!overlayWin) return;
    overlayWin.setIgnoreMouseEvents(false);
    overlayWin.webContents.send("riftbuddy:settings-mode");
    setTimeout(() => {
      overlayWin?.setIgnoreMouseEvents(true, { forward: true });
    }, 5000);
  });

  ipcMain.on("riftbuddy:exit-settings-mode", () => {
    overlayWin?.setIgnoreMouseEvents(true, { forward: true });
  });
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
  if (leagueTrackInterval) clearInterval(leagueTrackInterval);
});
app.on("window-all-closed", () => app.quit());
