import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  envDir: "..",
  server: {
    port: 5173,
    strictPort: true,
  },
  define: {
    "import.meta.env.VITE_RIFTBUDDY_WS_URL": JSON.stringify(
      loadEnv(mode, "..", "VITE_").VITE_RIFTBUDDY_WS_URL ?? "ws://localhost:8001/ws"
    )
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        draft: resolve(__dirname, "src/draft/draft.html"),
      },
    },
  },
}));
