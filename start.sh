#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_BIN="$BACKEND_DIR/.venv/bin/uvicorn"
LOG_DIR="$PROJECT_ROOT/storage/logs"
PID_DIR="$PROJECT_ROOT/storage/run"

BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

mkdir -p "$LOG_DIR" "$PID_DIR"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

is_project_process() {
  local pid="$1"
  [[ -d "/proc/$pid" ]] || return 1
  [[ "$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)" == "$PROJECT_ROOT" || \
     "$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)" == "$BACKEND_DIR" || \
     "$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)" == "$FRONTEND_DIR" ]] || return 1
  return 0
}

stop_pid() {
  local pid="$1"
  if ! kill -0 "$pid" 2>/dev/null; then
    return 0
  fi

  log "Stopping project process PID $pid"
  kill "$pid" 2>/dev/null || true

  for _ in {1..20}; do
    kill -0 "$pid" 2>/dev/null || return 0
    sleep 0.25
  done

  log "Process PID $pid did not stop gracefully; forcing termination"
  kill -KILL "$pid" 2>/dev/null || true
}

stop_saved_process() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    [[ "$pid" =~ ^[0-9]+$ ]] && stop_pid "$pid"
    rm -f "$pid_file"
  fi
}

stop_matching_project_processes() {
  local pid cmd cwd
  for pid in /proc/[0-9]*; do
    pid="${pid##*/}"
    [[ "$pid" == "$$" ]] && continue
    is_project_process "$pid" || continue
    cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
    cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"

    if [[ "$cwd" == "$PROJECT_ROOT" && "$cmd" == *"backend.app.main:app"* ]] ||
       [[ "$cwd" == "$FRONTEND_DIR" && "$cmd" == *"vite"* ]]; then
      stop_pid "$pid"
    fi
  done
}

wait_for_http() {
  local url="$1"
  local label="$2"
  for _ in {1..30}; do
    if curl -fsS -o /dev/null "$url" 2>/dev/null; then
      log "$label is ready: $url"
      return 0
    fi
    sleep 1
  done
  log "ERROR: $label did not become ready: $url"
  return 1
}

log "Project root: $PROJECT_ROOT"
log "Stopping existing # hasep processes"
stop_saved_process "$BACKEND_PID_FILE"
stop_saved_process "$FRONTEND_PID_FILE"
stop_matching_project_processes

if [[ ! -x "$BACKEND_BIN" ]]; then
  log "ERROR: Backend environment not found: $BACKEND_BIN"
  log "Create it first with: python3 -m venv backend/.venv"
  exit 1
fi

if [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
  log "ERROR: Frontend package.json not found: $FRONTEND_DIR/package.json"
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  log "Frontend dependencies are missing; installing with npm install"
  (cd "$FRONTEND_DIR" && npm install)
fi

log "Starting FastAPI on port 8000"
(
  cd "$PROJECT_ROOT"
  exec "$BACKEND_BIN" backend.app.main:app --host 0.0.0.0 --port 8000 --reload
) >>"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
printf '%s\n' "$BACKEND_PID" >"$BACKEND_PID_FILE"

log "Starting Vite frontend on port 5173"
(
  cd "$FRONTEND_DIR"
  exec npm run dev -- --host 0.0.0.0
) >>"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
printf '%s\n' "$FRONTEND_PID" >"$FRONTEND_PID_FILE"

if ! wait_for_http "http://127.0.0.1:8000/api/docs" "Backend"; then
  log "Backend log: $BACKEND_LOG"
  exit 1
fi

if ! wait_for_http "http://127.0.0.1:5173" "Frontend"; then
  log "Frontend log: $FRONTEND_LOG"
  exit 1
fi

log "# hasep is running"
log "Frontend: http://localhost:5173"
log "Backend docs: http://localhost:8000/api/docs"
log "Backend log: $BACKEND_LOG"
log "Frontend log: $FRONTEND_LOG"
