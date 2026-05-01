import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("riftBuddy", {
  onRequestAdvice: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on("riftbuddy:request-advice", handler);
    return () => ipcRenderer.removeListener("riftbuddy:request-advice", handler);
  },
  onToggleLanguage: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on("riftbuddy:toggle-language", handler);
    return () => ipcRenderer.removeListener("riftbuddy:toggle-language", handler);
  }
});
