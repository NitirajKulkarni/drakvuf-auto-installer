# Contributing to DRAKVUF Sandbox Auto-Installer

Thank you for your interest in contributing to **`drakvuf-auto-installer`**!

This project provides an automated deployment framework for DRAKVUF Sandbox and LibVMI. Contributions that improve reliability, support additional distributions, or enhance pre-flight diagnostics are welcome.

## Code of Conduct

Please maintain a respectful, constructive, and collaborative tone in all discussions and pull requests.

## Development Workflow

1. **Fork the repository** on GitHub.
2. **Create a topic branch**:
   ```bash
   git checkout -b feature/my-enhancement
   ```
3. **Set up local development**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt # or: pip install typer rich pydantic tomli
   ```
4. **Validate syntax and linting**:
   ```bash
   python3 -m compileall src
   bash -n install.sh
   bash -n diagnose.sh
   ```
5. **Commit with clean conventional commits**:
   - `feat: add support for Xen 4.20`
   - `fix: resolve PDB symbol download retry loop`
   - `docs: update pre-flight hardware recommendations`
6. **Submit a Pull Request**.

## Architecture Guidelines

- All phase handlers belong in `src/drakvuf_auto/phases/`.
- Ensure all file modifications support the atomic state engine (`state.py`).
- Keep shell wrapper scripts compatible with strict POSIX / Bash standards (`set -euo pipefail`).
