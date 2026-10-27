#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

printf '==> Running Seam 1: GTK3 CSS denylist and headless Eww runtime...\n'
"${REPO_DIR}/tests/check-seam1-gtk.sh"

printf '\n==> Running Seam 2: JSON schema contract and fixture pipeline...\n'
python3 "${REPO_DIR}/tests/check-seam2-schema.py"

printf '\n==> All per-ticket verification seams passed.\n'
