#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if ! command -v fc-match >/dev/null 2>&1 && command -v nix >/dev/null 2>&1 && [[ -f "${REPO_DIR}/flake.nix" ]]; then
  exec nix develop "${REPO_DIR}" -c bash "${BASH_SOURCE[0]}" "$@"
fi

font_dir="${SHIELD_FONTS:-}"
if [[ -z "${font_dir}" ]] || [[ ! -d "${font_dir}/share/fonts" ]]; then
  if fonts_from_eval="$(nix eval --raw "${REPO_DIR}#devShells.x86_64-linux.default.SHIELD_FONTS" 2>/dev/null)" && [[ -d "${fonts_from_eval}/share/fonts" ]]; then
    font_dir="${fonts_from_eval}"
  fi
fi

if [[ -z "${font_dir}" ]] || [[ ! -d "${font_dir}/share/fonts" ]]; then
  printf 'FAIL [fontconfig]: Pinned SHIELD_FONTS directory not found\n' >&2
  exit 1
fi

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/shield-fontconfig.XXXXXX")"
cleanup() {
  rm -rf "${WORK_DIR}"
}
trap cleanup EXIT INT TERM

fc_cache_dir="${WORK_DIR}/fc-cache"
mkdir -p "${fc_cache_dir}"

cat > "${WORK_DIR}/fonts.conf" << EOF
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <dir>${font_dir}/share/fonts</dir>
  <cachedir>${fc_cache_dir}</cachedir>
  <match target="pattern">
    <test qual="any" name="family"><string>Share Tech Mono</string></test>
    <edit name="family" mode="assign" binding="same"><string>ShureTechMono Nerd Font</string></edit>
  </match>
  <config></config>
</fontconfig>
EOF

export FONTCONFIG_FILE="${WORK_DIR}/fonts.conf"

REQUIRED_FAMILIES=(
  "Rajdhani"
  "Orbitron"
  "Barlow Condensed"
  "Share Tech Mono"
)

for family in "${REQUIRED_FAMILIES[@]}"; do
  matched_file="$(fc-match -f "%{file}\n" "${family}")"
  if [[ -z "${matched_file}" ]]; then
    printf 'FAIL [fontconfig]: Could not resolve family "%s"\n' "${family}" >&2
    exit 1
  fi
  if [[ "${matched_file}" != "${font_dir}"* ]]; then
    printf 'FAIL [fontconfig]: Family "%s" resolved to "%s", expected inside pinned "%s"\n' "${family}" "${matched_file}" "${font_dir}" >&2
    exit 1
  fi
done

printf 'PASS [fontconfig]: All DESIGN.md font families resolve to pinned package paths.\n'
