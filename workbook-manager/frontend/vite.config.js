import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: `npm run dev` proxies /api to the FastAPI server on :8050.
// Prod: `npm run build` emits dist/, which FastAPI serves directly.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5183,
    proxy: {
      "/api": "http://127.0.0.1:8050",
    },
  },
});
