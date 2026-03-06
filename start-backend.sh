#!/usr/bin/env bash
set -euo pipefail

# Common install location for `uv` on macOS/Linux when installed via the official installer.
export PATH="$HOME/.local/bin:$PATH"

cd "$(dirname "$0")/packages/backend"

if command -v uv >/dev/null 2>&1; then
    UV_CMD=(uv)
elif python3 -m uv --version >/dev/null 2>&1; then
    UV_CMD=(python3 -m uv)
else
    echo "Error: uv is not installed or not on PATH." >&2
    echo "Install it from https://docs.astral.sh/uv/getting-started/installation/" >&2
    echo "If uv is already installed, add \$HOME/.local/bin to your PATH." >&2
    exit 1
fi

# Load .env if present
if [ -f .env ]; then
    echo "==> Loading .env"
    set -a
    source .env
    set +a
fi

echo "==> Installing backend dependencies..."
"${UV_CMD[@]}" sync

echo "==> AI_PROVIDER=${AI_PROVIDER:-openai}"
echo "==> Starting backend server on http://localhost:8000"
"${UV_CMD[@]}" run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
