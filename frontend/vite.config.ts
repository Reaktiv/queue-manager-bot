import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    // Tunnel xizmatlari (Cloudflare, Ngrok) ishlashi uchun barcha hostlarga ruxsat beramiz
    allowedHosts: true,
    // Mini App faqat frontend tunneli orqali ochiladi (backend alohida tashqi
    // manzilga ega emas). /api so'rovlarini shu yer orqali backend'ga
    // proksilaymiz, shunda tunnel manzili har safar o'zgarsa ham (masalan,
    // Cloudflare quick tunnel qayta ishga tushganda) frontend kodini yoki
    // .env'ni qayta sozlash shart bo'lmaydi.
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
  },
});