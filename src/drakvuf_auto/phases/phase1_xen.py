"""Phase 1: Xen Hypervisor Deployment & GRUB Configuration.

Author: Nitiraj Kulkarni
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path

from drakvuf_auto.command import command_exists, run_command
from drakvuf_auto.config import DrakvufAutoConfig
from drakvuf_auto.diagnostics import SystemDiagnostics
from drakvuf_auto.exceptions import RebootRequiredError, XenInstallationError
from drakvuf_auto.state import StateManager

logger = logging.getLogger("drakvuf_auto.phase1")

RESUME_SERVICE_TEMPLATE = """[Unit]
Description=DRAKVUF Sandbox Auto-Installer Post-Reboot Resume Unit
After=multi-user.target xencommons.service
ConditionPathExists={project_root}/state/state.json

[Service]
Type=oneshot
User=root
WorkingDirectory={project_root}
ExecStart=/bin/bash {project_root}/install.sh --resume
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""


def execute_phase_1(config: DrakvufAutoConfig, state: StateManager, project_root: Path) -> None:
    """Deploy Xen Hypervisor, configure GRUB microkernel parameters, and prepare reboot."""
    phase_name = "phase_1_xen_install"
    if state.is_phase_completed(phase_name):
        logger.info("[bold green]Phase 1 (Xen Installation) already completed. Skipping.[/bold green]")
        return

    # Check if host is already running in Xen Dom0
    diag = SystemDiagnostics().run_all_checks()
    if diag.is_xen_active and diag.dom0_active:
        logger.info("[bold green]System is already running under Xen Dom0. Marking Phase 1 complete.[/bold green]")
        state.complete_phase(phase_name)
        return

    state.start_phase(phase_name)
    logger.info("Starting Phase 1: Xen Hypervisor Deployment & GRUB Configuration...")

    # Step 1: Install build dependencies & Xen packages
    step_pkg = "install_xen_prerequisites"
    if not state.is_step_completed(phase_name, step_pkg):
        state.start_step(phase_name, step_pkg)
        logger.info("Installing Xen toolchain and virtualization libraries...")
        pkgs = [
            "wget", "curl", "git", "build-essential", "make", "gcc", "clang",
            "bridge-utils", "iproute2", "libssl-dev", "bison", "flex",
            "libaio-dev", "libglib2.0-dev", "libpixman-1-dev", "iasl",
            "libjson-c-dev", "ninja-build", "meson", "kpartx"
        ]
        run_command(["apt-get", "update", "-y"], stream=False)
        run_command(["apt-get", "install", "-y"] + pkgs, stream=True)
        state.complete_step(phase_name, step_pkg)

    # Step 2: Install Xen Hypervisor packages
    step_xen = "deploy_xen_hypervisor"
    if not state.is_step_completed(phase_name, step_xen):
        state.start_step(phase_name, step_xen)
        logger.info("Installing Xen Hypervisor and tools...")
        # Check if xen-system-amd64 / xen-tools is in repo
        run_command(["apt-get", "install", "-y", "xen-hypervisor-amd64", "xen-tools"], stream=True, check=False)
        state.complete_step(phase_name, step_xen)

    # Step 3: Configure GRUB commandline parameters for VMI and Altp2m
    step_grub = "configure_xen_grub"
    if not state.is_step_completed(phase_name, step_grub):
        state.start_step(phase_name, step_grub)
        logger.info("Configuring GRUB microkernel parameters for Xen Dom0...")

        grub_default = Path("/etc/default/grub")
        if grub_default.exists():
            content = grub_default.read_text(encoding="utf-8")
            xen_cmdline = f'GRUB_CMDLINE_XEN_DEFAULT="{config.xen.grub_cmdline}"\n'

            # Backup grub configuration
            backup_grub = project_root / "backups" / "grub.default.bak"
            backup_grub.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(grub_default, backup_grub)

            # Update or append GRUB_CMDLINE_XEN_DEFAULT
            if "GRUB_CMDLINE_XEN_DEFAULT=" in content:
                import re
                content = re.sub(r'GRUB_CMDLINE_XEN_DEFAULT=.*', xen_cmdline.strip(), content)
            else:
                content += "\n" + xen_cmdline

            grub_default.write_text(content, encoding="utf-8")

        # Configure Xen kernel modules
        modules_file = Path("/etc/modules")
        if modules_file.exists():
            mod_content = modules_file.read_text(encoding="utf-8")
            for mod in ["xen-evtchn", "xen-privcmd", "xen-gntdev"]:
                if mod not in mod_content:
                    mod_content += f"\n{mod}\n"
            modules_file.write_text(mod_content, encoding="utf-8")

        # Update GRUB
        run_command(["update-grub"], stream=True)
        state.complete_step(phase_name, step_grub)

    # Step 4: Install Systemd Auto-Resume Unit for Post-Reboot Handshake
    step_resume = "install_resume_service"
    if not state.is_step_completed(phase_name, step_resume):
        state.start_step(phase_name, step_resume)
        logger.info("Setting up systemd post-reboot auto-resume handshake service...")

        resume_unit_path = Path("/etc/systemd/system/drakvuf-installer-resume.service")
        unit_content = RESUME_SERVICE_TEMPLATE.format(project_root=project_root.resolve())
        resume_unit_path.write_text(unit_content, encoding="utf-8")

        run_command(["systemctl", "daemon-reload"], stream=False)
        run_command(["systemctl", "enable", "drakvuf-installer-resume.service"], stream=False)
        state.complete_step(phase_name, step_resume)

    state.set_reboot_pending(True)
    state.complete_phase(phase_name)
    logger.info("[bold yellow]✓ Phase 1 Complete: Host is configured for Xen Hypervisor.[/bold yellow]")
    logger.info("[bold red]REBOOT REQUIRED: Host must now reboot into the Xen microkernel (Dom0).[/bold red]")

    if config.xen.allow_auto_reboot:
        logger.info("[bold cyan]Auto-reboot enabled. Initiating system reboot in 3 seconds...[/bold cyan]")
        run_command(["sleep", "3"], stream=False, check=False)
        run_command(["systemctl", "reboot"], stream=False, check=False)
        raise RebootRequiredError(
            "Host system is rebooting into Xen Dom0. Upon reboot, the installer will automatically resume from Phase 2."
        )
    else:
        raise RebootRequiredError(
            "Xen hypervisor installation requires a host reboot into Dom0. "
            "Please reboot the host system (sudo reboot). The installer will resume automatically upon boot."
        )
