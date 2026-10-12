"""Command Line Interface for DRAKVUF Sandbox Auto-Installer.

Author: Nitiraj Kulkarni
"""

import logging
import sys
from pathlib import Path
from typing import Optional

try:
    import typer
    TYPER_AVAILABLE = True
except ImportError:
    TYPER_AVAILABLE = False

from drakvuf_auto.diagnostics import SystemDiagnostics
from drakvuf_auto.logging_setup import print_banner, setup_logging
from drakvuf_auto.orchestrator import DrakvufOrchestrator
from drakvuf_auto.state import StateManager

if TYPER_AVAILABLE:
    app = typer.Typer(
        name="drakvuf-auto",
        help="Automated installer and manager for DRAKVUF Sandbox.",
        add_completion=False,
    )

    @app.command()
    def install(
        config_path: Path = typer.Option(
            Path("config.toml"), "--config", "-c", help="Path to config.toml"
        ),
        resume: bool = typer.Option(
            False, "--resume", "-r", help="Resume from last completed checkpoint"
        ),
        debug: bool = typer.Option(
            False, "--debug", "-d", help="Enable debug level logging"
        ),
    ):
        """Execute or resume DRAKVUF Sandbox installation pipeline."""
        project_root = Path(__file__).resolve().parents[2]
        log_level = logging.DEBUG if debug else logging.INFO
        log_file = project_root / "logs" / "install.log"
        setup_logging(log_file=log_file, level=log_level)

        orchestrator = DrakvufOrchestrator(
            config_path=config_path, project_root=project_root
        )
        orchestrator.run_installation(resume=resume)

    @app.command()
    def diagnose(
        min_ram: int = typer.Option(8, "--min-ram", help="Minimum required RAM in GB"),
        min_disk: int = typer.Option(40, "--min-disk", help="Minimum required disk in GB"),
    ):
        """Run deep hardware, CPU, and Xen hypervisor diagnostics."""
        project_root = Path(__file__).resolve().parents[2]
        setup_logging(level=logging.INFO)
        print_banner("DRAKVUF Pre-Flight Diagnostics", "Probing hardware and hypervisor environment")

        diag = SystemDiagnostics(min_ram_gb=min_ram, min_disk_gb=min_disk)
        result = diag.run_all_checks()

        if result.passed:
            print("\n[SUCCESS] Host meets all requirements for DRAKVUF Sandbox.")
        else:
            print(f"\n[FAILURE] Issues detected: {'; '.join(result.issues)}")
            sys.exit(1)

    @app.command()
    def status():
        """Display current phase status and checkpoint state."""
        project_root = Path(__file__).resolve().parents[2]
        state_file = project_root / "state" / "state.json"
        state = StateManager(state_file)

        print("\n=== DRAKVUF Sandbox Deployment Status ===")
        print(f"Reboot Pending:   {state.state.reboot_pending}")
        print(f"Reboot Completed: {state.state.reboot_completed}")
        print("\nPhases:")
        for name, record in state.state.phases.items():
            print(f"  - {name}: {record.status.value}")
        print("=========================================\n")

    @app.command()
    def reset():
        """Reset deployment state and start clean."""
        project_root = Path(__file__).resolve().parents[2]
        state_file = project_root / "state" / "state.json"
        state = StateManager(state_file)
        state.reset()
        print("[SUCCESS] Deployment state has been reset.")


def main():
    if TYPER_AVAILABLE:
        app()
    else:
        # Fallback for bootstrap environment
        import argparse
        parser = argparse.ArgumentParser(description="DRAKVUF Auto-Installer")
        parser.add_argument("command", choices=["install", "diagnose", "status", "reset"])
        parser.add_argument("--resume", action="store_true")
        args = parser.parse_args()

        project_root = Path(__file__).resolve().parents[2]
        if args.command == "install":
            orchestrator = DrakvufOrchestrator(
                config_path=Path("config.toml"), project_root=project_root
            )
            orchestrator.run_installation(resume=args.resume)
        elif args.command == "diagnose":
            diag = SystemDiagnostics()
            res = diag.run_all_checks()
            print(f"Diagnostics: Passed={res.passed}")


if __name__ == "__main__":
    main()
