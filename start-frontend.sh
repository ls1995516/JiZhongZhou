#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/packages/frontend"

echo "==> Installing frontend dependencies..."
npm install

echo "==> Starting frontend dev server on http://localhost:5173"
echo "==> API requests proxy to http://localhost:8000 (backend must be running)"
npm run dev
