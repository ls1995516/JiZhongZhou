#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/packages/backend"

# Load .env if present
if [ -f .env ]; then
    echo "==> Loading .env"
    set -a
    source .env
    set +a
fi

echo "==> Installing backend dependencies..."
uv sync

echo "==> AI_PROVIDER=${AI_PROVIDER:-openai}"
echo "==> Starting backend server on http://localhost:8000"
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
