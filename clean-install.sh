#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [[ $EUID -ne 0 ]]; then
    echo "[-] Error: Run clean-install as root (sudo ./clean-install.sh)" >&2
    exit 1
fi

echo "[!] Warning: Resetting all DRAKVUF state and performing fresh installation..."
rm -f "${SCRIPT_DIR}/state/state.json"
rm -f /etc/systemd/system/drakvuf-installer-resume.service 2>/dev/null || true

exec ./install.sh "$@"
