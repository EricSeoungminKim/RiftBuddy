import { app, BrowserWindow, globalShortcut } from "electron";
import path from "path";

const isDev = process.env.NODE_ENV === "development";
const isOverlay = process.env.RIFTBUDDY_OVERLAY === "1" || !isDev;

function createWindow(): BrowserWindow {
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
      preload: path.join(__dirname, "preload.js")
    }
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

app.whenReady().then(() => {
  const win = createWindow();
  globalShortcut.register("CommandOrControl+Shift+B", () => {
    win.webContents.send("riftbuddy:request-advice");
  });
  globalShortcut.register("CommandOrControl+Shift+L", () => {
    win.webContents.send("riftbuddy:toggle-language");
  });
});
app.on("will-quit", () => globalShortcut.unregisterAll());
app.on("window-all-closed", () => app.quit());
