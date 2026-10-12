#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python3"
if [[ -x "${VENV_PYTHON}" ]]; then
    exec "${VENV_PYTHON}" -m drakvuf_auto.cli status "$@"
else
    exec python3 -m drakvuf_auto.cli status "$@"
fi
