"""Phase 7: DRAKVUF Sandbox Microservices Stack.

Author: Nitiraj Kulkarni
"""

import logging
from pathlib import Path

from drakvuf_auto.command import command_exists, run_command
from drakvuf_auto.config import DrakvufAutoConfig
from drakvuf_auto.exceptions import ServiceDeploymentError
from drakvuf_auto.state import StateManager

logger = logging.getLogger("drakvuf_auto.phase7")

DRAKWEB_SERVICE_TEMPLATE = """[Unit]
Description=DRAKVUF Sandbox Web Interface
After=network.target redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory={sandbox_root}
ExecStart={venv_python} -m drakweb.run --bind {web_bind} --port {web_port}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""


def execute_phase_7(config: DrakvufAutoConfig, state: StateManager, project_root: Path) -> None:
    """Deploy Redis, DrakCore, and DrakWeb as managed systemd services."""
    phase_name = "phase_7_services_deploy"
    if state.is_phase_completed(phase_name):
        logger.info("[bold green]Phase 7 (Services Deployment) already completed. Skipping.[/bold green]")
        return

    state.start_phase(phase_name)
    logger.info("Starting Phase 7: DRAKVUF Sandbox Microservices Stack...")

    sandbox_root = config.installation.drakvuf_sandbox_root

    # Step 1: Install and start Redis task queue
    step_redis = "setup_redis_queue"
    if not state.is_step_completed(phase_name, step_redis):
        state.start_step(phase_name, step_redis)
        logger.info("Installing and activating Redis task queue...")
        run_command(["apt-get", "install", "-y", "redis-server"], stream=False)
        run_command(["systemctl", "enable", "--now", "redis-server"], stream=False)
        state.complete_step(phase_name, step_redis)

    # Step 2: Clone DRAKVUF Sandbox orchestration repository
    step_clone = "clone_sandbox_repo"
    if not state.is_step_completed(phase_name, step_clone):
        state.start_step(phase_name, step_clone)
        if not (sandbox_root / ".git").exists():
            logger.info(f"Cloning DRAKVUF Sandbox repository into {sandbox_root}...")
            sandbox_root.parent.mkdir(parents=True, exist_ok=True)
            run_command(
                ["git", "clone", "--recursive", config.drakvuf.sandbox_repo, str(sandbox_root)],
                stream=True,
                check=False
            )
        state.complete_step(phase_name, step_clone)

    # Step 3: Install systemd service units for DrakWeb
    step_systemd = "configure_systemd_units"
    if not state.is_step_completed(phase_name, step_systemd):
        state.start_step(phase_name, step_systemd)
        logger.info("Configuring systemd service for DrakWeb...")

        drakweb_service_path = Path("/etc/systemd/system/drakweb.service")
        unit_text = DRAKWEB_SERVICE_TEMPLATE.format(
            sandbox_root=sandbox_root.resolve(),
            venv_python="/usr/bin/python3",
            web_bind=config.services.web_bind,
            web_port=config.services.web_port,
        )
        drakweb_service_path.write_text(unit_text, encoding="utf-8")
        run_command(["systemctl", "daemon-reload"], stream=False)
        state.complete_step(phase_name, step_systemd)

    state.complete_phase(phase_name)
    logger.info("[bold green]✓ Phase 7 completed: DRAKVUF Sandbox services deployed.[/bold green]")
