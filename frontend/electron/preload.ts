import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("riftBuddy", {
  onRequestAdvice: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on("riftbuddy:request-advice", handler);
    return () =>
      ipcRenderer.removeListener("riftbuddy:request-advice", handler);
  },
  onRequestMatchup: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on("riftbuddy:request-matchup", handler);
    return () => ipcRenderer.removeListener("riftbuddy:request-matchup", handler);
  },
  onRequestItems: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on("riftbuddy:request-items", handler);
    return () => ipcRenderer.removeListener("riftbuddy:request-items", handler);
  },
  onRequestMacro: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on("riftbuddy:request-macro", handler);
    return () => ipcRenderer.removeListener("riftbuddy:request-macro", handler);
  },
  onToggleLanguage: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on("riftbuddy:toggle-language", handler);
    return () =>
      ipcRenderer.removeListener("riftbuddy:toggle-language", handler);
  },
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
  showPostGameWindow: () => ipcRenderer.send("riftbuddy:show-postgame-window"),
  exitSettingsMode: () => ipcRenderer.send("riftbuddy:exit-settings-mode"),
});
