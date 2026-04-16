#!/usr/bin/env bash
# Start the Golf Reservation Chatbot
#
# Usage:
#   ./scripts/start_server.sh           # Start in production mode
#   ./scripts/start_server.sh --reload  # Start with auto-reload (dev)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
else
    echo "Python is not installed or not on PATH."
    exit 1
fi

# Load .env if present
if [ -f .env ]; then
    echo "📄 Loading .env"
    set -a
    source .env
    set +a
fi

# Seed the database (idempotent)
echo "🗄️  Initializing database..."
"$PYTHON_BIN" -m backend.db.seed_data

# Start FastAPI
echo "🚀 Starting Golf Reservation Chatbot..."
echo "   API docs: http://localhost:${PORT:-8000}/docs"
echo ""
"$PYTHON_BIN" -m uvicorn backend.host.app:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    "$@"
