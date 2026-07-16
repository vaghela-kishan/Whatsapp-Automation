import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend runs on :8000. Vite proxies /api there so the browser talks to a
// single origin in dev (no CORS friction) and the app stays deploy-portable.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
