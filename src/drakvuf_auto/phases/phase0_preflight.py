"""Phase 0: Pre-flight Hardware & Environment Diagnostics.

Author: Nitiraj Kulkarni
"""

import json
import logging
from dataclasses import asdict
from pathlib import Path

from drakvuf_auto.config import DrakvufAutoConfig
from drakvuf_auto.diagnostics import SystemDiagnostics
from drakvuf_auto.exceptions import PreFlightCheckError
from drakvuf_auto.state import StateManager

logger = logging.getLogger("drakvuf_auto.phase0")

try:
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


def execute_phase_0(config: DrakvufAutoConfig, state: StateManager, project_root: Path) -> None:
    """Execute pre-flight hardware and environment diagnostics."""
    phase_name = "phase_0_preflight"
    if state.is_phase_completed(phase_name):
        logger.info("[bold green]Phase 0 (Pre-flight) already completed. Skipping.[/bold green]")
        return

    state.start_phase(phase_name)
    logger.info("Starting Phase 0: Pre-Flight Hardware & System Qualification...")

    state.start_step(phase_name, "hardware_probe")
    diagnostics = SystemDiagnostics(
        min_ram_gb=config.hardware.min_ram_gb,
        min_disk_gb=config.guest.disk_size_gb
    )
    result = diagnostics.run_all_checks()

    # Save diagnostic report to disk
    reports_dir = project_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / "diagnostic_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2)

    # Display diagnostic table
    if RICH_AVAILABLE and console:
        table = Table(title="DRAKVUF Sandbox Pre-Flight Diagnostic Matrix", border_style="cyan")
        table.add_column("Component", style="bold white")
        table.add_column("Detected Value", style="yellow")
        table.add_column("Status", style="bold")

        table.add_row(
            "Processor Vendor",
            "Intel" if result.is_intel else "Non-Intel",
            "[green]PASS[/green]" if result.is_intel else "[red]FAIL[/red]"
        )
        table.add_row("CPU Model", result.cpu_model, "[cyan]INFO[/cyan]")
        table.add_row("CPU Virtualization (VT-x / vmx)", str(result.has_vmx), "[green]PASS[/green]" if result.has_vmx else "[red]FAIL[/red]")
        table.add_row("Extended Page Tables (EPT)", str(result.has_ept), "[green]PASS[/green]" if result.has_ept else "[red]FAIL[/red]")
        table.add_row("Physical RAM", f"{result.total_ram_gb} GB", "[green]PASS[/green]" if result.total_ram_gb >= config.hardware.min_ram_gb else "[yellow]WARN[/yellow]")
        table.add_row("Free Storage", f"{result.free_disk_gb} GB", "[green]PASS[/green]" if result.free_disk_gb >= config.guest.disk_size_gb else "[red]FAIL[/red]")
        table.add_row("Host OS", f"{result.os_distro} {result.os_release}", "[cyan]INFO[/cyan]")
        table.add_row("Hypervisor Mode", "Xen Dom0" if result.is_xen_active else "Bare-Metal Linux", "[blue]READY FOR XEN[/blue]" if not result.is_xen_active else "[green]XEN ACTIVE[/green]")
        console.print(table)
    else:
        logger.info(f"CPU: {result.cpu_model} (Intel: {result.is_intel}, VMX: {result.has_vmx}, EPT: {result.has_ept})")
        logger.info(f"RAM: {result.total_ram_gb} GB | Free Storage: {result.free_disk_gb} GB")

    for warn in result.warnings:
        logger.warning(f"[yellow]Diagnostic Warning:[/yellow] {warn}")

    if not result.passed:
        error_msg = "; ".join(result.issues)
        state.fail_step(phase_name, "hardware_probe", error_msg)
        state.fail_phase(phase_name, error_msg)
        raise PreFlightCheckError(f"Pre-flight qualification failed: {error_msg}")

    state.complete_step(phase_name, "hardware_probe", asdict(result))
    state.complete_phase(phase_name)
    logger.info("[bold green]✓ Phase 0 completed: System is fully qualified for DRAKVUF Sandbox.[/bold green]")
