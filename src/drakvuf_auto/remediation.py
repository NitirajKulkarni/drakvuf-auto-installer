"""Automated Remediation Subsystem for DRAKVUF Sandbox.

Author: Nitiraj Kulkarni
"""

import logging
from pathlib import Path
from typing import Optional

from drakvuf_auto.command import command_exists, run_command

logger = logging.getLogger("drakvuf_auto.remediation")


class AutoRemediator:
    """Handles automated remediation for known issues in Xen, LibVMI, and DrakWeb."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def apply_ovmf_patch(self, xen_source_dir: Path) -> bool:
        """Apply Tianocore OVMF submodule fix to Xen Config.mk."""
        patch_file = self.project_root / "templates" / "patches" / "ovmf_subhook.patch"
        config_mk = xen_source_dir / "Config.mk"

        if not patch_file.exists() or not config_mk.exists():
            return False

        logger.info(f"Applying OVMF stability patch to {config_mk}...")
        try:
            run_command(["patch", "-p1", "-i", str(patch_file)], cwd=xen_source_dir, stream=True)
            return True
        except Exception as e:
            logger.warning(f"Could not apply OVMF patch cleanly: {e}")
            return False

    def fix_xen_modules(self) -> None:
        """Ensure all Xen virtualization kernel modules are actively loaded."""
        modules = ["xen-evtchn", "xen-privcmd", "xen-gntdev"]
        for mod in modules:
            run_command(["modprobe", mod], stream=False, check=False)
        logger.info("Reloaded Xen kernel modules.")

    def fix_ldconfig(self) -> None:
        """Update library cache for LibVMI shared objects."""
        ld_conf = Path("/etc/ld.so.conf.d/drakvuf.conf")
        ld_conf.write_text("/usr/local/lib\n", encoding="utf-8")
        run_command(["ldconfig"], stream=False, check=False)
        logger.info("Updated dynamic linker cache with /usr/local/lib.")

    def restart_services(self) -> None:
        """Restart core daemon services."""
        services = ["xencommons", "redis-server", "drakweb"]
        for svc in services:
            run_command(["systemctl", "restart", svc], stream=False, check=False)
        logger.info("Restarted DRAKVUF daemon services.")
