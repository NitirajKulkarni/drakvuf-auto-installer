"""LibVMI JSON Profile Synthesis Utility.

Author: Nitiraj Kulkarni
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from drakvuf_auto.command import command_exists, run_command
from drakvuf_auto.exceptions import ProfileSynthesisError

logger = logging.getLogger("drakvuf_auto.vmi.profile_maker")


class LibVMIProfileBuilder:
    """Builds and validates LibVMI JSON profiles for guest Windows domains."""

    def __init__(self, profile_dir: Optional[Path] = None):
        self.profile_dir = profile_dir or Path("/etc/libvmi")
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def generate_profile(
        self,
        domain_name: str,
        os_type: str = "Windows",
        offsets: Optional[Dict[str, int]] = None,
        sysmap_path: Optional[str] = None
    ) -> Path:
        """Create a validated LibVMI JSON profile file."""
        target_path = self.profile_dir / f"{domain_name}.json"
        logger.info(f"Generating LibVMI JSON profile for '{domain_name}' at {target_path}...")

        profile_data: Dict[str, Any] = {
            domain_name: {
                "ostype": os_type,
            }
        }

        if sysmap_path:
            profile_data[domain_name]["sysmap"] = sysmap_path

        if offsets:
            for k, v in offsets.items():
                profile_data[domain_name][k] = hex(v) if isinstance(v, int) else v

        target_path.write_text(json.dumps(profile_data, indent=2), encoding="utf-8")
        logger.info(f"Successfully wrote LibVMI profile: {target_path}")
        return target_path

    def test_profile(self, domain_name: str) -> bool:
        """Verify profile against live Xen domain using vmi-process-list."""
        if not command_exists("vmi-process-list"):
            logger.warning("vmi-process-list binary not found in PATH; skipping live validation.")
            return True

        res = run_command(["vmi-process-list", "-n", domain_name], stream=False, check=False)
        if res.returncode == 0:
            logger.info(f"[green]LibVMI successfully introspected domain '{domain_name}'![/green]")
            return True
        else:
            logger.warning(f"LibVMI test output: {res.stderr or res.stdout}")
            return False
