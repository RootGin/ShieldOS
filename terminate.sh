#!/usr/bin/env bash
# Aggressively terminate all eww instances (graceful first, then SIGKILL for hung/crashed processes)
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Gracefully stopping eww daemon via IPC..."
eww -c "${REPO_DIR}" kill >/dev/null 2>&1 || true

sleep 0.5

# If any eww processes remain (e.g. hung daemon, frozen GUI, orphaned scripts), SIGTERM them
if pgrep -x eww >/dev/null 2>&1 || pgrep -f "eww -c" >/dev/null 2>&1; then
    echo "==> Sending SIGTERM to remaining eww processes..."
    pkill -TERM -x eww >/dev/null 2>&1 || true
    pkill -TERM -f "eww -c" >/dev/null 2>&1 || true
    sleep 0.5
fi

# Force kill (SIGKILL) any stubborn or zombie/crashed eww processes
if pgrep -x eww >/dev/null 2>&1 || pgrep -f "eww -c" >/dev/null 2>&1; then
    echo "==> Force killing (SIGKILL) unresponsive eww processes..."
    pkill -9 -x eww >/dev/null 2>&1 || true
    pkill -9 -f "eww -c" >/dev/null 2>&1 || true
    sleep 0.2
fi

# Clean up stale eww IPC sockets if left behind in XDG_RUNTIME_DIR or /tmp
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
rm -f "${RUNTIME_DIR}"/eww*sock* 2>/dev/null || true
rm -f /tmp/eww*sock* 2>/dev/null || true

echo "==> All eww processes terminated."
