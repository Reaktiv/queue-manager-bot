import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// `@types/node` o'rnatilmagan, shuning uchun faqat kerakli qismini e'lon qilamiz.
declare const process: { env: Record<string, string | undefined> };

const BACKEND_PORT = process.env.BACKEND_PORT ?? "8005";
const FRONTEND_PORT = Number(process.env.PORT ?? 5175);

export default defineConfig({
  plugins: [react()],
  server: {
    port: FRONTEND_PORT,
    strictPort: true,
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
        target: `http://localhost:${BACKEND_PORT}`,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
  },
});