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

# Load .env if present
if [ -f .env ]; then
    echo "📄 Loading .env"
    set -a
    source .env
    set +a
fi

# Seed the database (idempotent)
echo "🗄️  Initializing database..."
python -m backend.db.seed_data

# Start FastAPI
echo "🚀 Starting Golf Reservation Chatbot..."
echo "   API docs: http://localhost:${PORT:-8000}/docs"
echo ""
uvicorn backend.host.app:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    "$@"
