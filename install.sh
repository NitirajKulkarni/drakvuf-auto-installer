#!/usr/bin/env bash
# ==============================================================================
# DRAKVUF Sandbox Automated Installer - Entrypoint Script
# Author: Nitiraj Kulkarni
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# 1. Require root execution
if [[ $EUID -ne 0 ]]; then
    echo "[-] Error: DRAKVUF Sandbox installer must be executed as root (sudo ./install.sh)" >&2
    exit 1
fi

echo "[*] Initializing DRAKVUF Sandbox Auto-Installer environment..."

# 2. Ensure base system dependencies are present
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv > /dev/null

# 3. Create and activate local virtual environment
VENV_DIR="${SCRIPT_DIR}/.venv"
if [[ ! -d "${VENV_DIR}" ]]; then
    echo "[*] Creating dedicated Python virtual environment at ${VENV_DIR}..."
    python3 -m venv "${VENV_DIR}"
fi

# 4. Install Python CLI dependencies
"${VENV_DIR}/bin/pip" install --quiet --upgrade pip
"${VENV_DIR}/bin/pip" install --quiet rich typer pydantic tomli

# 5. Execute orchestrator via CLI
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"
exec "${VENV_DIR}/bin/python3" -m drakvuf_auto.cli install "$@"
