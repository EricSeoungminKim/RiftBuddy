import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  envDir: "..",
  define: {
    "import.meta.env.VITE_RIFTBUDDY_WS_URL": JSON.stringify(
      loadEnv(mode, "..", "VITE_").VITE_RIFTBUDDY_WS_URL ?? "ws://localhost:8001/ws"
    )
  }
}));
