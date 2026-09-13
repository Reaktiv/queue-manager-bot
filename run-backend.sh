#!/usr/bin/env bash
# Backend (8005) + Bot — bitta buyruq bilan ishga tushiradi.
# Ctrl+C bosilsa ikkalasi ham to'xtaydi.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8005}"
cd "$ROOT"

echo "==> Postgres + Redis (docker) ko'tarilmoqda..."
docker compose up -d postgres redis

echo "==> Docker'dagi app konteynerlari to'xtatilmoqda (port/bot konflikti bo'lmasin)..."
docker compose stop backend bot scheduler frontend nginx >/dev/null 2>&1 || true

source "$ROOT/backend/.venv/bin/activate"

# Bot kutubxonalari faqat birinchi marta o'rnatiladi
if ! python -c "import aiogram" >/dev/null 2>&1; then
  echo "==> Bot kutubxonalari o'rnatilmoqda (birinchi marta)..."
  pip install -q -r "$ROOT/bot/requirements.txt"
fi

echo "==> Migratsiyalar (alembic upgrade head)..."
(cd "$ROOT/backend" && alembic upgrade head)

pids=()
cleanup() {
  trap - INT TERM EXIT
  echo
  echo "==> To'xtatilmoqda..."
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM EXIT

echo "==> Backend:  http://localhost:$BACKEND_PORT/docs"
(cd "$ROOT/backend" && exec uvicorn src.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT") \
  > >(sed -u 's/^/[backend] /') 2>&1 &
pids+=($!)

# Backend ko'tarilguncha kutamiz
for _ in $(seq 1 40); do
  curl -sf -o /dev/null "http://127.0.0.1:$BACKEND_PORT/openapi.json" && break
  sleep 0.5
done

# Bot ildizdagi .env ni o'qiydi, u yerda BACKEND_URL=8000 turibdi - shu yerda
# haqiqiy portga almashtiramiz (eksport qilingan qiymat .env dan ustun turadi).
echo "==> Bot ishga tushmoqda (BACKEND_URL=http://127.0.0.1:$BACKEND_PORT)"
export BACKEND_URL="http://127.0.0.1:$BACKEND_PORT"
(cd "$ROOT/bot" && exec python main.py) \
  > >(sed -u 's/^/[bot]     /') 2>&1 &
pids+=($!)

echo "==> Tayyor. To'xtatish uchun Ctrl+C"
wait
