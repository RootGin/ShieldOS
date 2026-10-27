#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_DIR="$(cd "${REPO_DIR}/.." && pwd)"

fail() {
  local check_name="$1"
  local message="$2"
  printf 'FAIL [%s]: %s\n' "${check_name}" "${message}" >&2
  exit 1
}

resolve_target() {
  local target="$1"
  if [[ "${target}" == *"/"* ]] || [[ "${target}" == *.png ]]; then
    local cleaned="${target%.png}"
    CAPTURE_FILE="${REPO_DIR}/tests/captures/${cleaned}.png"
    GOLDEN_FILE="${REPO_DIR}/tests/goldens/${cleaned}.png"
    DIFF_FILE="${REPO_DIR}/tests/captures/diff-${cleaned//\//-}.png"
    COMPARE_FILE="${REPO_DIR}/tests/captures/compare-${cleaned//\//-}.png"
  else
    CAPTURE_FILE="${REPO_DIR}/tests/captures/milestone-${target}.png"
    GOLDEN_FILE="${REPO_DIR}/tests/goldens/milestone-${target}.png"
    DIFF_FILE="${REPO_DIR}/tests/captures/diff-${target}.png"
    COMPARE_FILE="${REPO_DIR}/tests/captures/compare-${target}.png"
  fi
}

render_and_capture() {
  local out_file="$1"
  local work_dir
  work_dir="$(mktemp -d "${TMPDIR:-/tmp}/shield-seam3.XXXXXX")"

  local sway_pid=""
  local eww_pid=""

  inner_cleanup() {
    if [[ -n "${eww_pid:-}" ]]; then
      eww -c "${REPO_DIR}" kill >/dev/null 2>&1 || true
      kill "${eww_pid}" >/dev/null 2>&1 || true
      wait "${eww_pid}" 2>/dev/null || true
    fi
    if [[ -n "${sway_pid:-}" ]]; then
      kill "${sway_pid}" >/dev/null 2>&1 || true
      wait "${sway_pid}" 2>/dev/null || true
    fi
    if [[ -n "${work_dir:-}" ]] && [[ -d "${work_dir}" ]]; then
      rm -rf "${work_dir}"
    fi
  }
  trap inner_cleanup RETURN INT TERM

  local xdg_runtime="${work_dir}/runtime"
  local xdg_config="${work_dir}/config"
  local xdg_data="${work_dir}/data"
  local xdg_cache="${work_dir}/cache"
  mkdir -p "${xdg_runtime}" "${xdg_config}/gtk-3.0" "${xdg_data}" "${xdg_cache}"
  chmod 700 "${xdg_runtime}"

  cat > "${xdg_config}/gtk-3.0/settings.ini" << 'EOF'
[Settings]
gtk-theme-name=Adwaita
gtk-icon-theme-name=Adwaita
gtk-font-name=Sans 10
gtk-cursor-theme-name=Adwaita
gtk-cursor-theme-size=24
gtk-toolbar-style=GTK_TOOLBAR_BOTH_HORIZ
gtk-toolbar-icon-size=GTK_ICON_SIZE_LARGE_TOOLBAR
gtk-button-images=1
gtk-menu-images=1
gtk-enable-event-sounds=0
gtk-enable-input-feedback-sounds=0
gtk-xft-antialias=1
gtk-xft-hinting=1
gtk-xft-hintstyle=hintslight
gtk-xft-rgba=rgb
EOF

  local font_dir="${SHIELD_FONTS:-}"
  if [[ -z "${font_dir}" ]] || [[ ! -d "${font_dir}/share/fonts" ]]; then
    if fonts_from_eval="$(nix eval --raw "${REPO_DIR}#devShells.x86_64-linux.default.SHIELD_FONTS" 2>/dev/null)" && [[ -d "${fonts_from_eval}/share/fonts" ]]; then
      font_dir="${fonts_from_eval}"
    fi
  fi

  if [[ -n "${font_dir}" ]] && [[ -d "${font_dir}/share/fonts" ]]; then
    local fc_cache_dir="${work_dir}/fc-cache"
    mkdir -p "${fc_cache_dir}"
    cat > "${work_dir}/fonts.conf" << EOF
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <dir>${font_dir}/share/fonts</dir>
  <cachedir>${fc_cache_dir}</cachedir>
  <config></config>
</fontconfig>
EOF
    export FONTCONFIG_FILE="${work_dir}/fonts.conf"
  fi

  export XDG_RUNTIME_DIR="${xdg_runtime}"
  export XDG_CONFIG_HOME="${xdg_config}"
  export XDG_DATA_HOME="${xdg_data}"
  export XDG_CACHE_HOME="${xdg_cache}"
  export GDK_SCALE=1
  export GDK_DPI_SCALE=1
  export GDK_BACKEND=wayland
  export SHIELD_FIXTURE="frozen"

  local sway_cfg="${work_dir}/sway.cfg"
  cat > "${sway_cfg}" << 'EOF'
output HEADLESS-1 resolution 1920x1080 position 0 0 scale 1
default_border none
default_floating_border none
EOF

  WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 WLR_RENDERER=pixman sway -c "${sway_cfg}" >"${work_dir}/sway.log" 2>&1 &
  sway_pid=$!

  local wayland_socket=""
  for _ in $(seq 1 60); do
    for sock in "${xdg_runtime}"/wayland-*; do
      if [[ -S "${sock}" ]]; then
        wayland_socket="$(basename "${sock}")"
        break 2
      fi
    done
    if ! kill -0 "${sway_pid}" 2>/dev/null; then
      fail "headless-sway" "sway exited prematurely: $(cat "${work_dir}/sway.log")"
    fi
    sleep 0.05
  done

  if [[ -z "${wayland_socket}" ]]; then
    fail "headless-sway" "Timed out waiting for sway Wayland socket: $(cat "${work_dir}/sway.log")"
  fi
  export WAYLAND_DISPLAY="${wayland_socket}"

  local eww_log="${work_dir}/eww.log"
  eww -c "${REPO_DIR}" daemon --no-daemonize >"${eww_log}" 2>&1 &
  eww_pid=$!

  local ping_ok=0
  for _ in $(seq 1 60); do
    if ! kill -0 "${eww_pid}" 2>/dev/null; then
      fail "eww-daemon" "eww daemon exited prematurely: $(cat "${eww_log}")"
    fi
    if ping_out="$(eww -c "${REPO_DIR}" ping 2>/dev/null)" && [[ "${ping_out}" == *"pong"* ]]; then
      ping_ok=1
      break
    fi
    sleep 0.05
  done

  if [[ "${ping_ok}" -ne 1 ]]; then
    fail "eww-daemon" "Timed out waiting for eww daemon ping: $(cat "${eww_log}")"
  fi

  local windows=()
  mapfile -t windows < <(
    python3 -c '
import glob, re, os, sys
repo = sys.argv[1]
files = [os.path.join(repo, "eww.yuck")] + sorted(glob.glob(os.path.join(repo, "yuck", "*.yuck")))
windows = []
for p in files:
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            text = f.read()
        for m in re.finditer(r"\(\s*defwindow\s+([a-zA-Z0-9_-]+)", text):
            if m.group(1) not in windows:
                windows.append(m.group(1))
for w in windows:
    print(w)
' "${REPO_DIR}"
  )

  if [[ "${#windows[@]}" -eq 0 ]]; then
    fail "yuck-windows" "No (defwindow ...) definitions found in ${REPO_DIR}"
  fi

  local open_err="${work_dir}/eww-open.log"
  if ! eww -c "${REPO_DIR}" open-many "${windows[@]}" >"${open_err}" 2>&1; then
    fail "eww-open-windows" "eww open-many failed: $(cat "${open_err}") $(cat "${eww_log}")"
  fi

  local active_ok=0
  for _ in $(seq 1 60); do
    local active_out
    active_out="$(eww -c "${REPO_DIR}" active-windows 2>&1 || true)"
    local all_found=1
    for win in "${windows[@]}"; do
      if ! grep -Eq "(^|[[:space:]]|: )${win}$" <<<"${active_out}"; then
        all_found=0
        break
      fi
    done
    if [[ "${all_found}" -eq 1 ]]; then
      active_ok=1
      break
    fi
    sleep 0.05
  done

  if [[ "${active_ok}" -ne 1 ]]; then
    fail "active-windows" "Timed out waiting for windows (${windows[*]}) to become active. Logs: $(cat "${eww_log}")"
  fi

  local prev_snap="${work_dir}/snap_prev.png"
  local curr_snap="${work_dir}/snap_curr.png"
  local settled=0

  for _ in $(seq 1 50); do
    grim "${curr_snap}"
    if [[ -f "${prev_snap}" ]]; then
      if cmp -s "${prev_snap}" "${curr_snap}"; then
        settled=1
        break
      fi
      local ae_diff
      if ae_diff="$(magick compare -metric AE "${prev_snap}" "${curr_snap}" null: 2>&1)" && [[ "${ae_diff}" == "0 (0)" || "${ae_diff}" == "0" ]]; then
        settled=1
        break
      fi
    fi
    cp "${curr_snap}" "${prev_snap}"
    sleep 0.05
  done

  if [[ "${settled}" -ne 1 ]]; then
    fail "render-settle" "Capture did not settle to two consecutive identical frames within timeout"
  fi

  mkdir -p "$(dirname "${out_file}")"
  cp "${curr_snap}" "${out_file}"
}

subcommand_capture() {
  local target="$1"
  resolve_target "${target}"
  printf '==> Capturing render for target %s...\n' "${target}"
  render_and_capture "${CAPTURE_FILE}"
  printf 'CAPTURED: %s\n' "${CAPTURE_FILE}"
}

subcommand_check() {
  local target="$1"
  resolve_target "${target}"
  if [[ ! -f "${GOLDEN_FILE}" ]]; then
    fail "missing-golden" "Golden file not found: ${GOLDEN_FILE}"
  fi
  printf '==> Capturing render for target %s...\n' "${target}"
  render_and_capture "${CAPTURE_FILE}"
  printf 'CAPTURED: %s\n' "${CAPTURE_FILE}"

  printf '==> Comparing against golden %s...\n' "${GOLDEN_FILE}"
  mkdir -p "$(dirname "${DIFF_FILE}")"
  local compare_out
  compare_out="$(magick compare -metric AE -fuzz 2% "${CAPTURE_FILE}" "${GOLDEN_FILE}" "${DIFF_FILE}" 2>&1 || true)"
  local diff_count
  diff_count="$(echo "${compare_out}" | awk '{printf "%.0f\n", $1}')"
  if ! [[ "${diff_count}" =~ ^[0-9]+$ ]]; then
    fail "compare-metric" "magick compare failed to produce a valid pixel count: ${compare_out}"
  fi

  local dims
  dims="$(magick identify -format "%w %h" "${CAPTURE_FILE}" 2>/dev/null || echo "1920 1080")"
  local img_w img_h total_pixels
  read -r img_w img_h <<< "${dims}"
  total_pixels=$(( img_w * img_h ))
  local max_diff_pixels=$(( total_pixels / 1000 ))

  if (( diff_count > max_diff_pixels )); then
    fail "seam3-golden" "${CAPTURE_FILE} differs from ${GOLDEN_FILE} by ${diff_count} pixels (> ${max_diff_pixels} threshold, 0.1%). Diff image written to: ${DIFF_FILE}"
  fi

  rm -f "${DIFF_FILE}"
  printf 'PASS [seam3-golden]: %s matches %s (%d differing pixels <= %d threshold at 2%% fuzz).\n' "${CAPTURE_FILE}" "${GOLDEN_FILE}" "${diff_count}" "${max_diff_pixels}"
}

subcommand_approve() {
  local target="$1"
  shift
  local has_yes=0
  for arg in "$@"; do
    if [[ "${arg}" == "--yes" ]]; then
      has_yes=1
      break
    fi
  done
  if [[ "${has_yes}" -ne 1 ]]; then
    fail "approve-safety" "Refusing to approve without explicit --yes flag."
  fi
  resolve_target "${target}"
  if [[ ! -f "${CAPTURE_FILE}" ]]; then
    fail "approve-missing-capture" "No capture found at ${CAPTURE_FILE}. Run capture first."
  fi
  mkdir -p "$(dirname "${GOLDEN_FILE}")"
  cp -v "${CAPTURE_FILE}" "${GOLDEN_FILE}"
  printf 'APPROVED: Promoted %s to %s\n' "${CAPTURE_FILE}" "${GOLDEN_FILE}"
}

subcommand_compare() {
  local target="$1"
  resolve_target "${target}"
  if [[ ! -f "${CAPTURE_FILE}" ]]; then
    printf '==> Capturing render for target %s...\n' "${target}"
    render_and_capture "${CAPTURE_FILE}"
    printf 'CAPTURED: %s\n' "${CAPTURE_FILE}"
  fi
  local ref_img=""
  if [[ -f "${REPO_DIR}/reference/shield-os.png" ]]; then
    ref_img="${REPO_DIR}/reference/shield-os.png"
  elif [[ -f "${WORKSPACE_DIR}/reference/shield-os.png" ]]; then
    ref_img="${WORKSPACE_DIR}/reference/shield-os.png"
  else
    fail "reference-missing" "Reference image reference/shield-os.png not found"
  fi
  mkdir -p "$(dirname "${COMPARE_FILE}")"
  magick "${CAPTURE_FILE}" \( "${ref_img}" -resize 1920x1080\! \) +append "${COMPARE_FILE}"
  printf 'CREATED [seam3-compare]: Side-by-side fidelity comparison image written to %s\n' "${COMPARE_FILE}"
}

main() {
  if [[ $# -lt 2 ]]; then
    printf 'Usage: %s <capture|check|approve|compare> <N> [--yes]\n' "$0" >&2
    exit 1
  fi

  local action="$1"
  local target="$2"
  shift 2

  case "${action}" in
    capture)
      subcommand_capture "${target}"
      ;;
    check)
      subcommand_check "${target}"
      ;;
    approve)
      subcommand_approve "${target}" "$@"
      ;;
    compare)
      subcommand_compare "${target}"
      ;;
    *)
      fail "invalid-command" "Unknown subcommand '${action}'. Expected: capture, check, approve, compare."
      ;;
  esac
}

main "$@"
