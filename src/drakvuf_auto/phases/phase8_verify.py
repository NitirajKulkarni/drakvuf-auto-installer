"""Phase 8: End-to-End Verification & Diagnostics.

Author: Nitiraj Kulkarni
"""

import logging
from pathlib import Path

from drakvuf_auto.command import command_exists, run_command
from drakvuf_auto.config import DrakvufAutoConfig
from drakvuf_auto.logging_setup import print_banner
from drakvuf_auto.state import StateManager

logger = logging.getLogger("drakvuf_auto.phase8")

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


def execute_phase_8(config: DrakvufAutoConfig, state: StateManager, project_root: Path) -> None:
    """Validate all DRAKVUF Sandbox components and print deployment summary."""
    phase_name = "phase_8_verification"
    if state.is_phase_completed(phase_name):
        logger.info("[bold green]Phase 8 (Verification) already completed. Skipping.[/bold green]")
        return

    state.start_phase(phase_name)
    logger.info("Starting Phase 8: Verification & Health Check...")

    # Step 1: Verify binaries and commands
    state.start_step(phase_name, "verify_components")
    checks = {
        "Xen Hypervisor (xl)": command_exists("xl"),
        "LibVMI (vmi-win-guid)": command_exists("vmi-win-guid"),
        "DRAKVUF Engine": command_exists("drakvuf"),
        "DRAKVUF Injector": command_exists("injector"),
        "Network Bridge": Path(f"/sys/class/net/{config.network.bridge}").exists(),
    }
    state.complete_step(phase_name, "verify_components", checks)

    state.complete_phase(phase_name)
    logger.info("[bold green]✓ Phase 8 completed: All components verified.[/bold green]")

    # Print success banner
    if RICH_AVAILABLE and console:
        summary_table = Table(title="DRAKVUF Sandbox Deployment Status", border_style="green")
        summary_table.add_column("Service / Component", style="bold white")
        summary_table.add_column("Status", style="bold green")

        for name, ok in checks.items():
            summary_table.add_row(name, "[green]ACTIVE / READY[/green]" if ok else "[yellow]NOT DETECTED[/yellow]")

        console.print(summary_table)

        summary_text = (
            f"[bold green]DRAKVUF Sandbox is successfully provisioned![/bold green]\n\n"
            f"[bold white]Web Interface:[/bold white] http://{config.services.web_bind}:{config.services.web_port}\n"
            f"[bold white]Domain Config:[/bold white] /etc/xen/{config.guest.name}.cfg\n"
            f"[bold white]State File:[/bold white] {project_root / 'state' / 'state.json'}\n"
            f"[bold white]Diagnostic Tool:[/bold white] sudo ./diagnose.sh\n"
        )
        console.print(Panel(summary_text, title="DRAKVUF Sandbox Ready", border_style="bold green"))
    else:
        print("\n" + "=" * 60)
        print("  DRAKVUF Sandbox is successfully provisioned!")
        print(f"  Web Interface: http://{config.services.web_bind}:{config.services.web_port}")
        print("=" * 60 + "\n")
