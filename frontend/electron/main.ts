import { app, BrowserWindow, globalShortcut } from "electron";
import path from "path";

const isDev = process.env.NODE_ENV === "development";
const isOverlay = process.env.RIFTBUDDY_OVERLAY === "1" || !isDev;

function createOverlayWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 520,
    height: 360,
    x: 1360,
    y: 90,
    transparent: isOverlay,
    frame: !isOverlay,
    alwaysOnTop: true,
    skipTaskbar: isOverlay,
    resizable: !isOverlay,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  win.setAlwaysOnTop(true, "screen-saver");
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  if (isOverlay) {
    win.setIgnoreMouseEvents(true, { forward: true });
  }

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
    title: "RiftBuddy — Draft",
    frame: true,
    alwaysOnTop: true,
    show: false,
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

app.whenReady().then(() => {
  const overlayWin = createOverlayWindow();
  const draftWin = createDraftWindow();

  globalShortcut.register("CommandOrControl+Shift+B", () => {
    overlayWin.webContents.send("riftbuddy:request-advice");
  });
  globalShortcut.register("CommandOrControl+Shift+Space", () => {
    overlayWin.webContents.send("riftbuddy:request-voice-question");
  });
  globalShortcut.register("CommandOrControl+Shift+L", () => {
    overlayWin.webContents.send("riftbuddy:toggle-language");
  });
  globalShortcut.register("CommandOrControl+Shift+D", () => {
    if (draftWin.isVisible()) {
      draftWin.hide();
    } else {
      draftWin.show();
      draftWin.focus();
    }
  });
});

app.on("will-quit", () => globalShortcut.unregisterAll());
app.on("window-all-closed", () => app.quit());
