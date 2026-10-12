#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [[ $EUID -ne 0 ]]; then
    echo "[-] Error: Run uninstall as root (sudo ./uninstall.sh)" >&2
    exit 1
fi

echo "[!] Warning: You are about to uninstall DRAKVUF Sandbox services and configurations."
read -p "Are you sure you want to proceed? [y/N]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "[*] Aborted."
    exit 0
fi

echo "[*] Stopping and disabling DRAKVUF services..."
systemctl stop drakweb 2>/dev/null || true
systemctl disable drakweb 2>/dev/null || true
rm -f /etc/systemd/system/drakweb.service
rm -f /etc/systemd/system/drakvuf-installer-resume.service

systemctl daemon-reload

echo "[*] Removing network bridge..."
ip link set dev xenbr0 down 2>/dev/null || true
ip link delete dev xenbr0 2>/dev/null || true

echo "[*] Cleaning state..."
rm -f "${SCRIPT_DIR}/state/state.json"

echo "[+] DRAKVUF Sandbox uninstalled successfully."
