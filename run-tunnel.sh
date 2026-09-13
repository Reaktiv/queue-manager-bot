#!/usr/bin/env bash
# Mini App uchun ommaviy HTTPS tunnel (cloudflared).
#
# Nega ngrok emas: ngrok'ning bepul rejimi HTML sahifa so'ralganda o'zining
# "You are about to visit..." ogohlantirish sahifasini qaytaradi (ERR_NGROK_6024).
# Uni faqat maxsus header bilan chetlab o'tish mumkin, Telegram WebView esa
# header qo'sha olmaydi - natijada Mini App o'rniga o'sha sahifa ochiladi.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${FRONTEND_PORT:-5175}"

command -v cloudflared >/dev/null || { echo "cloudflared o'rnatilmagan"; exit 1; }

if ! curl -sf -o /dev/null "http://127.0.0.1:$PORT/"; then
  echo "OGOHLANTIRISH: $PORT portda frontend ishlamayapti."
  echo "Avval boshqa terminalda ./run-frontend.sh ni ishga tushiring."
  echo
fi

# Auth chetlab o'tish yoqiq holda tunnel ochish = ilovani hammaga ochib qo'yish
if grep -qE '^DEV_AUTH_BYPASS=true' "$ROOT/.env.local" 2>/dev/null; then
  echo "!!! XAVF: .env.local da DEV_AUTH_BYPASS=true."
  echo "!!! Tunnel ochiq bo'lsa, manzilni bilgan HAR KIM Super Admin bo'lib kiradi."
  echo "!!! Uni false qiling va backend'ni qayta ishga tushiring."
  echo
fi

echo "==> Tunnel ochilmoqda (http://localhost:$PORT)..."
echo "==> Chiqqan https://... manzilini BotFather -> /setmenubutton ga qo'ying."
echo
exec cloudflared tunnel --url "http://localhost:$PORT"
