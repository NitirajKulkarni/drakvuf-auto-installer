"""Phase 4: Network Bridge & Virtualization Storage Subsystem.

Author: Nitiraj Kulkarni
"""

import logging
from pathlib import Path

from drakvuf_auto.command import command_exists, run_command
from drakvuf_auto.config import DrakvufAutoConfig
from drakvuf_auto.exceptions import NetworkBridgeError
from drakvuf_auto.state import StateManager

logger = logging.getLogger("drakvuf_auto.phase4")


def execute_phase_4(config: DrakvufAutoConfig, state: StateManager, project_root: Path) -> None:
    """Configure Xen network bridge, DHCP daemon, and disk storage pool."""
    phase_name = "phase_4_network_storage"
    if state.is_phase_completed(phase_name):
        logger.info("[bold green]Phase 4 (Network & Storage) already completed. Skipping.[/bold green]")
        return

    state.start_phase(phase_name)
    logger.info("Starting Phase 4: Network Bridge & Virtualization Storage Subsystem...")

    bridge_name = config.network.bridge

    # Step 1: Create and configure Xen bridge
    step_bridge = "configure_xen_bridge"
    if not state.is_step_completed(phase_name, step_bridge):
        state.start_step(phase_name, step_bridge)
        logger.info(f"Setting up network bridge {bridge_name}...")

        # Create bridge if it doesn't exist
        run_command(["ip", "link", "add", "name", bridge_name, "type", "bridge"], check=False)
        run_command(["ip", "addr", "add", f"{config.network.gateway}/24", "dev", bridge_name], check=False)
        run_command(["ip", "link", "set", "dev", bridge_name, "up"], check=True)

        # Enable IPv4 forwarding
        run_command(["sysctl", "-w", "net.ipv4.ip_forward=1"], stream=False)

        # Configure NAT masquerade for guest network
        if command_exists("iptables"):
            run_command(
                ["iptables", "-t", "nat", "-A", "POSTROUTING", "-s", config.network.subnet, "-j", "MASQUERADE"],
                check=False
            )
        state.complete_step(phase_name, step_bridge)

    # Step 2: Configure dnsmasq for guest DHCP/DNS
    step_dns = "configure_dhcp_dns"
    if not state.is_step_completed(phase_name, step_dns):
        state.start_step(phase_name, step_dns)
        logger.info("Configuring dnsmasq for guest VM IP assignment...")

        run_command(["apt-get", "install", "-y", "dnsmasq"], stream=False)
        dnsmasq_conf = Path(f"/etc/dnsmasq.d/drakvuf-{bridge_name}.conf")
        conf_content = (
            f"interface={bridge_name}\n"
            f"dhcp-range={config.network.dhcp_start},{config.network.dhcp_end},255.255.255.0,12h\n"
            f"dhcp-option=3,{config.network.gateway}\n"
            f"dhcp-option=6,8.8.8.8,1.1.1.1\n"
        )
        dnsmasq_conf.write_text(conf_content, encoding="utf-8")
        run_command(["systemctl", "restart", "dnsmasq"], stream=False, check=False)
        state.complete_step(phase_name, step_dns)

    # Step 3: Prepare storage directory for virtual machine images
    step_storage = "prepare_storage_directory"
    if not state.is_step_completed(phase_name, step_storage):
        state.start_step(phase_name, step_storage)
        logger.info("Initializing storage directory for guest VM images...")
        image_dir = config.guest.disk_path.parent
        image_dir.mkdir(parents=True, exist_ok=True)
        state.complete_step(phase_name, step_storage)

    state.complete_phase(phase_name)
    logger.info("[bold green]✓ Phase 4 completed: Network bridge and storage pool ready.[/bold green]")
