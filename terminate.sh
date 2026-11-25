#!/usr/bin/env bash
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

collect_descendants() {
  local pid="$1"
  local child
  for child in $(pgrep -P "$pid" 2>/dev/null || true); do
    echo "$child"
    collect_descendants "$child"
  done
}

collect_target_pids() {
  local -A seen=()
  local pid cwd

  for pid in $(pgrep -x eww 2>/dev/null || true) $(pgrep -x .eww-wrapped 2>/dev/null || true); do
    seen["$pid"]=1
  done

  for pid in $(pgrep -f 'scripts/(telemetry|network-audio|compositor)\.py' 2>/dev/null || true); do
    [[ "$pid" == "$$" || "$pid" == "$PPID" ]] && continue
    cwd="$(readlink -f "/proc/${pid}/cwd" 2>/dev/null || true)"
    if [[ "$cwd" == "$REPO_DIR" ]] || grep -qF "${REPO_DIR}/scripts/" "/proc/${pid}/cmdline" 2>/dev/null; then
      seen["$pid"]=1
    fi
  done

  local roots=("${!seen[@]}")
  local desc
  for pid in "${roots[@]}"; do
    for desc in $(collect_descendants "$pid"); do
      seen["$desc"]=1
    done
  done

  unset "seen[$$]" "seen[$PPID]" 2>/dev/null || true
  printf '%s\n' "${!seen[@]}"
}

if command -v eww >/dev/null 2>&1; then
  echo "==> Gracefully closing eww windows and stopping daemon..."
  timeout 2 eww -c "${REPO_DIR}" close-all >/dev/null 2>&1 || true
  sleep 0.2
  timeout 2 eww -c "${REPO_DIR}" kill >/dev/null 2>&1 || true
  sleep 0.3
fi

mapfile -t TARGET_PIDS < <(collect_target_pids)
if (( ${#TARGET_PIDS[@]} > 0 )); then
  echo "==> Sending SIGTERM to remaining eww processes (${#TARGET_PIDS[@]})..."
  kill -TERM "${TARGET_PIDS[@]}" 2>/dev/null || true
  for _ in $(seq 1 10); do
    sleep 0.1
    mapfile -t TARGET_PIDS < <(collect_target_pids)
    (( ${#TARGET_PIDS[@]} == 0 )) && break
  done
fi

mapfile -t TARGET_PIDS < <(collect_target_pids)
if (( ${#TARGET_PIDS[@]} > 0 )); then
  echo "==> Force killing (SIGKILL) unresponsive eww processes (${#TARGET_PIDS[@]})..."
  kill -KILL "${TARGET_PIDS[@]}" 2>/dev/null || true
  sleep 0.2
fi

RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
rm -f "${RUNTIME_DIR}"/eww-server_* "${RUNTIME_DIR}"/eww*sock* 2>/dev/null || true
rm -f /tmp/eww-server_* /tmp/eww*sock* 2>/dev/null || true

echo "==> All eww processes terminated."
