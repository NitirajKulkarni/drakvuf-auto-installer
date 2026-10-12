"""Phase 2: Post-Reboot Verification & Handshake.

Author: Nitiraj Kulkarni
"""

import logging
from pathlib import Path

from drakvuf_auto.command import command_exists, run_command
from drakvuf_auto.config import DrakvufAutoConfig
from drakvuf_auto.diagnostics import SystemDiagnostics
from drakvuf_auto.exceptions import XenNotActiveError
from drakvuf_auto.state import StateManager

logger = logging.getLogger("drakvuf_auto.phase2")


def execute_phase_2(config: DrakvufAutoConfig, state: StateManager, project_root: Path) -> None:
    """Verify that system has successfully rebooted into Xen Dom0 and clean up resume service."""
    phase_name = "phase_2_xen_handshake"
    if state.is_phase_completed(phase_name):
        logger.info("[bold green]Phase 2 (Xen Handshake) already completed. Skipping.[/bold green]")
        return

    state.start_phase(phase_name)
    logger.info("Starting Phase 2: Post-Reboot Xen Dom0 Verification...")

    # Step 1: Probe hypervisor state
    state.start_step(phase_name, "verify_xen_active")
    diag = SystemDiagnostics().run_all_checks()

    if not diag.is_xen_active or not diag.dom0_active:
        error_msg = (
            "System is NOT running under Xen Dom0! The host either failed to reboot into Xen "
            "or the bootloader selected standard Linux instead of Xen in the GRUB menu."
        )
        logger.error(f"[bold red]{error_msg}[/bold red]")
        state.fail_step(phase_name, "verify_xen_active", error_msg)
        state.fail_phase(phase_name, error_msg)
        raise XenNotActiveError(error_msg)

    logger.info(f"[bold green]✓ Xen Hypervisor Active: {diag.xen_version or 'Detected'} (Domain-0 running).[/bold green]")
    state.complete_step(phase_name, "verify_xen_active", {"xen_version": diag.xen_version})

    # Step 2: Teardown auto-resume service
    state.start_step(phase_name, "cleanup_resume_service")
    resume_service = Path("/etc/systemd/system/drakvuf-installer-resume.service")
    if resume_service.exists():
        run_command(["systemctl", "disable", "drakvuf-installer-resume.service"], stream=False, check=False)
        resume_service.unlink()
        run_command(["systemctl", "daemon-reload"], stream=False, check=False)
        logger.info("Cleaned up temporary post-reboot systemd resume unit.")
    state.complete_step(phase_name, "cleanup_resume_service")

    state.set_reboot_completed(True)
    state.complete_phase(phase_name)
    logger.info("[bold green]✓ Phase 2 completed: Xen Dom0 verified and active.[/bold green]")
