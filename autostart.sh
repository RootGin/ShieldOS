#!/usr/bin/env bash
# Autostart script for shieldOS-eww
# Terminates any existing/hung eww instances first, then launches daemon and all windows.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Terminate existing or crashed eww processes cleanly
"${REPO_DIR}/terminate.sh" || true

# Run startup inside nix develop environment if needed, or directly if tools are present
if command -v nix >/dev/null 2>&1 && [ -f "${REPO_DIR}/flake.nix" ]; then
    exec nix develop "${REPO_DIR}" --command "${REPO_DIR}/bin/shield-open" "$@"
else
    exec "${REPO_DIR}/bin/shield-open" "$@"
fi
