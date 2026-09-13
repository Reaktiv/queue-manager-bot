#!/usr/bin/env bash
# Frontend (5175) — bitta buyruq bilan.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT/frontend"

[ -d node_modules ] || { echo "==> npm install (birinchi marta)..."; npm install; }

echo "==> Frontend: http://localhost:5175   (/api -> http://localhost:${BACKEND_PORT:-8005})"
exec npm run dev
