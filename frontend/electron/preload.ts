import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("riftBuddy", {
  onRequestAdvice: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on("riftbuddy:request-advice", handler);
    return () =>
      ipcRenderer.removeListener("riftbuddy:request-advice", handler);
  },
  onRequestVoiceQuestion: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on("riftbuddy:request-voice-question", handler);
    return () =>
      ipcRenderer.removeListener("riftbuddy:request-voice-question", handler);
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
  exitSettingsMode: () => ipcRenderer.send("riftbuddy:exit-settings-mode"),
});
