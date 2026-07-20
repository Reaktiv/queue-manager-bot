import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    // Tunnel xizmatlari (Cloudflare, Ngrok) ishlashi uchun barcha hostlarga ruxsat beramiz
    allowedHosts: true,
  },
  build: {
    outDir: "dist",
  },
});