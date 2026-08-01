import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Enable WebSocket upgrades for the game WS endpoint under /api.
      "/api": { target: "http://localhost:8000", ws: true },
      // Card art is served by the backend from backend/images/.
      "/images": "http://localhost:8000",
    },
  },
});
