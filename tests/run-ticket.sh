#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

printf '==> Running Seam 1: GTK3 CSS denylist and headless Eww runtime...\n'
"${REPO_DIR}/tests/check-seam1-gtk.sh"

printf '\n==> Running Seam 2: JSON schema contract and fixture pipeline...\n'
python3 "${REPO_DIR}/tests/check-seam2-schema.py"

printf '\n==> Running Seam 3 helpers self-test (crop & measure)...\n'
crop_out="${REPO_DIR}/tests/captures/crop-selftest-canvas-0_0_100_100-z6.png"
rm -f "${crop_out}"
"${REPO_DIR}/tests/check-seam3-golden.sh" crop selftest/canvas 0,0,100,100 6 >/dev/null
if [[ ! -f "${crop_out}" ]]; then
  printf 'FAIL [seam3-crop-selftest]: Cropped image not created\n' >&2
  exit 1
fi
crop_dims="$(magick identify -format "%wx%h" "${crop_out}")"
if [[ "${crop_dims}" != "600x600" ]]; then
  printf 'FAIL [seam3-crop-selftest]: Expected 600x600, got %s\n' "${crop_dims}" >&2
  exit 1
fi

measure_canvas="$("${REPO_DIR}/tests/check-seam3-golden.sh" measure selftest/canvas '#0E0F11' | tail -n 1)"
if [[ "${measure_canvas}" != "1920x1080 +0+0" ]]; then
  printf 'FAIL [seam3-measure-selftest]: Expected 1920x1080 +0+0, got %s\n' "${measure_canvas}" >&2
  exit 1
fi

measure_absent="$("${REPO_DIR}/tests/check-seam3-golden.sh" measure selftest/canvas '#FFFFFF' | tail -n 1)"
if [[ "${measure_absent}" != "0x0 +0+0" ]]; then
  printf 'FAIL [seam3-measure-selftest]: Expected 0x0 +0+0, got %s\n' "${measure_absent}" >&2
  exit 1
fi
printf 'PASS [seam3-helpers]: crop and measure self-test passed against selftest capture.\n'

printf '\n==> All per-ticket verification seams passed.\n'
