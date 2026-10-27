#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_DIR="$(cd "${REPO_DIR}/.." && pwd)"

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/shield-seam1.XXXXXX")"
export XDG_RUNTIME_DIR="${WORK_DIR}/runtime"
export XDG_CACHE_HOME="${WORK_DIR}/cache"
mkdir -p "${XDG_RUNTIME_DIR}" "${XDG_CACHE_HOME}"
chmod 700 "${XDG_RUNTIME_DIR}"

SWAY_PID=""
EWW_PID=""

cleanup() {
  local exit_code=$?
  if [[ -n "${EWW_PID}" ]]; then
    eww -c "${REPO_DIR}" kill >/dev/null 2>&1 || true
    kill "${EWW_PID}" >/dev/null 2>&1 || true
    wait "${EWW_PID}" 2>/dev/null || true
  fi
  if [[ -n "${SWAY_PID}" ]]; then
    kill "${SWAY_PID}" >/dev/null 2>&1 || true
    wait "${SWAY_PID}" 2>/dev/null || true
  fi
  rm -rf "${WORK_DIR}"
  exit "${exit_code}"
}
trap cleanup EXIT INT TERM

fail() {
  local check_name="$1"
  local message="$2"
  printf 'FAIL [%s]: %s\n' "${check_name}" "${message}" >&2
  exit 1
}

cd "${WORKSPACE_DIR}"

CSS_OUT="/tmp/shield.css"
SASS_ERR="${WORK_DIR}/sass.err"
if ! sass --no-source-map --silence-deprecation=import,global-builtin "shieldOS-eww/eww.scss" "${CSS_OUT}" 2>"${SASS_ERR}"; then
  fail "sass-compile" "sass failed to compile shieldOS-eww/eww.scss: $(cat "${SASS_ERR}")"
fi
if [[ -s "${SASS_ERR}" ]]; then
  fail "sass-compile" "sass emitted warnings: $(cat "${SASS_ERR}")"
fi

DENYLIST_LABELS=(
  "display: flex"
  "justify-content"
  "align-items"
  "flex-direction"
  "position"
  "z-index"
  "float"
  "clear"
  "::before"
  "::after"
  "text-overflow"
  "white-space"
  "-webkit-*"
  "appearance"
  "cursor"
  ":focus-visible"
  "@media"
  "var(--"
  "max-width"
  "max-height"
  "overflow"
  "line-height"
  "transition: all"
  "!important"
  "comma-separated @keyframes selectors"
  "animation-delay"
  "steps()"
  "8-digit hex colors (#RRGGBBAA)"
  "to top right"
  "two-position gradient color stops"
  "url()"
)

DENYLIST_PATTERNS=(
  "display[[:space:]]*:[[:space:]]*(inline-)?flex"
  "(^|[[:space:]{;])justify-content[[:space:]]*:"
  "(^|[[:space:]{;])align-items[[:space:]]*:"
  "(^|[[:space:]{;])flex-direction[[:space:]]*:"
  "(^|[[:space:]{;])position[[:space:]]*:"
  "(^|[[:space:]{;])z-index[[:space:]]*:"
  "(^|[[:space:]{;])float[[:space:]]*:"
  "(^|[[:space:]{;])clear[[:space:]]*:"
  "::?before"
  "::?after"
  "(^|[[:space:]{;])text-overflow[[:space:]]*:"
  "(^|[[:space:]{;])white-space[[:space:]]*:"
  "-webkit-[a-zA-Z0-9_-]+"
  "(^|[[:space:]{;])appearance[[:space:]]*:"
  "(^|[[:space:]{;])cursor[[:space:]]*:"
  ":focus-visible"
  "@media"
  "(var\(--|(^|[[:space:]{;])--[a-zA-Z0-9_-]+[[:space:]]*:)"
  "(^|[[:space:]{;])max-width[[:space:]]*:"
  "(^|[[:space:]{;])max-height[[:space:]]*:"
  "(^|[[:space:]{;])overflow(-x|-y)?[[:space:]]*:"
  "(^|[[:space:]{;])line-height[[:space:]]*:"
  "transition(-property)?[[:space:]]*:[[:space:]]*all([[:space:];,}]|$)"
  "!important"
  "(^|[;{}])[[:space:]]*([0-9]+%|from|to)[[:space:]]*,"
  "(^|[[:space:]{;])animation-delay[[:space:]]*:"
  "steps\([[:space:]]*[0-9]+"
  "(^|[^0-9a-fA-F])#[0-9a-fA-F]{8}([^0-9a-fA-F]|$)"
  "to[[:space:]]+top[[:space:]]+right"
  "(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)|hsla?\([^)]*\)|transparent)[[:space:]]+-?[0-9]+(\.[0-9]+)?(px|%|em|rem)?[[:space:]]+-?[0-9]+(\.[0-9]+)?(px|%|em|rem)?([[:space:],\)]|$)"
  "(^|[[:space:]{;:(-])url\("
)

for i in "${!DENYLIST_LABELS[@]}"; do
  label="${DENYLIST_LABELS[$i]}"
  pattern="${DENYLIST_PATTERNS[$i]}"
  if match="$(grep -En "${pattern}" "${CSS_OUT}" || true)" && [[ -n "${match}" ]]; then
    fail "css-denylist" "Forbidden GTK3 CSS construct '${label}' found in compiled CSS: ${match}"
  fi
done

if ! python3 "${REPO_DIR}/tests/check-yuck-triangles.py"; then
  fail "yuck-geometry" "Yuck triangle geometry validation failed"
fi

mapfile -t WINDOWS < <(
  python3 -c '
import glob, re, sys
files = ["shieldOS-eww/eww.yuck"] + sorted(glob.glob("shieldOS-eww/yuck/*.yuck"))
windows = []
for path in files:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for m in re.finditer(r"\(\s*defwindow\s+([a-zA-Z0-9_-]+)", text):
        if m.group(1) not in windows:
            windows.append(m.group(1))
for w in windows:
    print(w)
'
)

if [[ "${#WINDOWS[@]}" -eq 0 ]]; then
  fail "yuck-windows" "No (defwindow ...) definitions found in shieldOS-eww"
fi

SWAY_CFG="${WORK_DIR}/sway.cfg"
printf 'output HEADLESS-1 resolution 1920x1080\n' >"${SWAY_CFG}"

WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 WLR_RENDERER=pixman sway -c "${SWAY_CFG}" >"${WORK_DIR}/sway.log" 2>&1 &
SWAY_PID=$!

WAYLAND_SOCKET=""
for _ in $(seq 1 50); do
  for sock in "${XDG_RUNTIME_DIR}"/wayland-*; do
    if [[ -S "${sock}" ]]; then
      WAYLAND_SOCKET="$(basename "${sock}")"
      break 2
    fi
  done
  if ! kill -0 "${SWAY_PID}" 2>/dev/null; then
    fail "headless-sway" "sway exited prematurely: $(cat "${WORK_DIR}/sway.log")"
  fi
  sleep 0.1
done

if [[ -z "${WAYLAND_SOCKET}" ]]; then
  fail "headless-sway" "Timed out waiting for headless sway Wayland socket: $(cat "${WORK_DIR}/sway.log")"
fi

export WAYLAND_DISPLAY="${WAYLAND_SOCKET}"
export GDK_BACKEND=wayland
export SHIELD_FIXTURE="${SHIELD_FIXTURE:-frozen}"

EWW_LOG="${WORK_DIR}/eww.log"
eww -c shieldOS-eww daemon --no-daemonize >"${EWW_LOG}" 2>&1 &
EWW_PID=$!

PING_OK=0
for _ in $(seq 1 50); do
  if ! kill -0 "${EWW_PID}" 2>/dev/null; then
    fail "eww-daemon" "eww daemon exited prematurely: $(cat "${EWW_LOG}")"
  fi
  if ping_out="$(eww -c shieldOS-eww ping 2>/dev/null)" && [[ "${ping_out}" == *"pong"* ]]; then
    PING_OK=1
    break
  fi
  sleep 0.1
done

if [[ "${PING_OK}" -ne 1 ]]; then
  fail "eww-daemon" "Timed out waiting for eww daemon ping: $(cat "${EWW_LOG}")"
fi

OPEN_ERR="${WORK_DIR}/eww-open.log"
if ! eww -c shieldOS-eww open-many "${WINDOWS[@]}" >"${OPEN_ERR}" 2>&1; then
  fail "eww-open-windows" "eww open-many failed: $(cat "${OPEN_ERR}") $(cat "${EWW_LOG}")"
fi

sleep 0.5

if ! kill -0 "${EWW_PID}" 2>/dev/null; then
  fail "eww-daemon" "eww daemon crashed after opening windows: $(cat "${EWW_LOG}")"
fi

ACTIVE_OUT="$(eww -c shieldOS-eww active-windows 2>&1 || true)"
for win in "${WINDOWS[@]}"; do
  if ! grep -Eq "(^|[[:space:]]|: )${win}$" <<<"${ACTIVE_OUT}"; then
    fail "eww-active-windows" "Window '${win}' missing from active-windows (got: '${ACTIVE_OUT}'). Logs: $(cat "${EWW_LOG}")"
  fi
done

STATE_OUT="$(eww -c shieldOS-eww state --all 2>&1 || true)"
if [[ -z "${STATE_OUT}" ]] || ! grep -Eq "^[a-zA-Z0-9_-]+: .+" <<<"${STATE_OUT}"; then
  fail "eww-state" "eww state --all is not populated (got: '${STATE_OUT}'). Logs: $(cat "${EWW_LOG}")"
fi

if [[ "${SHIELD_FIXTURE}" == "frozen" ]]; then
  for expected in '"time":"17:32:14"' '"day":"21"' '"month_year":"NOV - 2025"' '"weekday":"FRI"'; do
    if ! grep -Fq "${expected}" <<<"${STATE_OUT}"; then
      fail "eww-state-frozen" "Expected ${expected} in eww state --all (got: '$(grep "^telemetry:" <<<"${STATE_OUT}" || true)')"
    fi
  done
fi

LOGS_CMD_OUT="$(timeout 1s eww -c shieldOS-eww logs 2>&1 || true)"
COMBINED_LOGS="$(cat "${EWW_LOG}" "${OPEN_ERR}" 2>/dev/null; printf '\n%s\n' "${LOGS_CMD_OUT}")"
FILTERED_LOGS="$(grep -v "Run \`eww logs\` to see any errors" <<<"${COMBINED_LOGS}" || true)"

if bad_logs="$(grep -E "(WARN|ERROR|Gtk-WARNING|Gtk-CRITICAL|error\[|error:|warning:|is not a valid property name|CssProviderError|ParseError|Failed to)" <<<"${FILTERED_LOGS}" || true)" && [[ -n "${bad_logs}" ]]; then
  fail "eww-logs" "Warnings or errors detected in eww logs: ${bad_logs}"
fi

printf 'PASS [seam1-gtk]: CSS denylist clean, windows active (%s), state populated, logs clean.\n' "${WINDOWS[*]}"
