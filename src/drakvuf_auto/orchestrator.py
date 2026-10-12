"""Master Lifecycle Orchestrator for DRAKVUF Sandbox Auto-Installer.

Author: Nitiraj Kulkarni
"""

import logging
from pathlib import Path
from typing import Optional

from drakvuf_auto.config import DrakvufAutoConfig, load_config
from drakvuf_auto.exceptions import RebootRequiredError
from drakvuf_auto.logging_setup import print_banner
from drakvuf_auto.phases.phase0_preflight import execute_phase_0
from drakvuf_auto.phases.phase1_xen import execute_phase_1
from drakvuf_auto.phases.phase2_resume import execute_phase_2
from drakvuf_auto.phases.phase3_engine import execute_phase_3
from drakvuf_auto.phases.phase4_network import execute_phase_4
from drakvuf_auto.phases.phase5_guest import execute_phase_5
from drakvuf_auto.phases.phase6_symbols import execute_phase_6
from drakvuf_auto.phases.phase7_services import execute_phase_7
from drakvuf_auto.phases.phase8_verify import execute_phase_8
from drakvuf_auto.state import StateManager

logger = logging.getLogger("drakvuf_auto.orchestrator")


class DrakvufOrchestrator:
    """Orchestrates the multi-phase deployment of DRAKVUF Sandbox."""

    def __init__(self, config_path: Path, project_root: Path):
        self.project_root = Path(project_root)
        self.config = load_config(config_path)
        self.state_file = self.project_root / "state" / "state.json"
        self.state = StateManager(self.state_file)

    def run_installation(self, resume: bool = False) -> None:
        """Execute the installation pipeline from start to finish."""
        print_banner(
            "DRAKVUF Sandbox Automated Installer",
            "Agentless Virtual Machine Introspection Deployment Suite"
        )

        try:
            # Phase 0: Pre-flight qualification
            execute_phase_0(self.config, self.state, self.project_root)

            # Phase 1: Xen Hypervisor installation & GRUB setup
            # If reboot was pending or this is a resume after reboot, skip to Phase 2
            if not self.state.state.reboot_completed:
                if not self.state.is_phase_completed("phase_1_xen_install"):
                    execute_phase_1(self.config, self.state, self.project_root)

                # Phase 2: Post-reboot handshake
                execute_phase_2(self.config, self.state, self.project_root)

            # Phase 3: DRAKVUF Engine & LibVMI
            execute_phase_3(self.config, self.state, self.project_root)

            # Phase 4: Network Bridge & Storage
            execute_phase_4(self.config, self.state, self.project_root)

            # Phase 5: Guest VM Configuration
            execute_phase_5(self.config, self.state, self.project_root)

            # Phase 6: Kernel Symbols & LibVMI Profile
            execute_phase_6(self.config, self.state, self.project_root)

            # Phase 7: Microservices Stack (Redis, DrakWeb)
            execute_phase_7(self.config, self.state, self.project_root)

            # Phase 8: Verification & Health Check
            execute_phase_8(self.config, self.state, self.project_root)

        except RebootRequiredError as e:
            logger.info(f"[bold yellow]{e}[/bold yellow]")
            return
        except Exception as e:
            logger.exception(f"[bold red]Installation aborted due to an unhandled error: {e}[/bold red]")
            raise
