#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

BACKEND_RELOAD=1
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

for arg in "$@"; do
    case "$arg" in
        --no-reload)
            BACKEND_RELOAD=0
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: ./scripts/start_app.sh [--no-reload]"
            exit 1
            ;;
    esac
done

cleanup() {
    if [[ -n "${BACKEND_PID:-}" ]]; then
        kill "$BACKEND_PID" >/dev/null 2>&1 || true
    fi
    if [[ -n "${FRONTEND_PID:-}" ]]; then
        kill "$FRONTEND_PID" >/dev/null 2>&1 || true
    fi
}

port_in_use() {
    lsof -ti tcp:"$1" >/dev/null 2>&1
}

find_available_port() {
    local port="$1"
    while port_in_use "$port"; do
        port=$((port + 1))
    done
    printf '%s' "$port"
}

wait_for_child_exit() {
    while true; do
        if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
            wait "$BACKEND_PID"
            return $?
        fi

        if ! kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
            wait "$FRONTEND_PID"
            return $?
        fi

        sleep 1
    done
}

trap cleanup EXIT INT TERM

cd "$PROJECT_ROOT"

if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

export VITE_SUPABASE_URL="${VITE_SUPABASE_URL:-${NEXT_PUBLIC_SUPABASE_URL:-${SUPABASE_URL:-}}}"
export VITE_SUPABASE_PUBLISHABLE_KEY="${VITE_SUPABASE_PUBLISHABLE_KEY:-${NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY:-${SUPABASE_PUBLISHABLE_KEY:-}}}"

SELECTED_FRONTEND_PORT="$(find_available_port "$FRONTEND_PORT")"

if [[ "$SELECTED_FRONTEND_PORT" != "$FRONTEND_PORT" ]]; then
    echo "Frontend port $FRONTEND_PORT is busy. Using $SELECTED_FRONTEND_PORT instead."
fi

echo "Starting backend and frontend..."
echo "Backend:  http://localhost:${PORT:-8000}"
echo "Frontend: http://localhost:${SELECTED_FRONTEND_PORT}"
echo ""

if [[ "$BACKEND_RELOAD" -eq 1 ]]; then
    ./scripts/start_server.sh --reload &
else
    ./scripts/start_server.sh &
fi
BACKEND_PID=$!

(cd frontend && npm run dev -- --host 0.0.0.0 --port "$SELECTED_FRONTEND_PORT" --strictPort) &
FRONTEND_PID=$!

wait_for_child_exit
