#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [[ $EUID -ne 0 ]]; then
    echo "[-] Error: Run repair as root (sudo ./repair.sh)" >&2
    exit 1
fi

echo "[*] Running DRAKVUF environment automated repair..."

# 1. Ensure Xen modules are loaded
modprobe xen-evtchn 2>/dev/null || true
modprobe xen-privcmd 2>/dev/null || true
modprobe xen-gntdev 2>/dev/null || true

# 2. Restart Xen services
systemctl restart xencommons 2>/dev/null || true
systemctl restart redis-server 2>/dev/null || true

# 3. Reload ldconfig for LibVMI
ldconfig

echo "[+] Automated repairs completed. Run ./diagnose.sh to verify."
