"""Post-Installation & Diagnostic Reporting Engine.

Author: Nitiraj Kulkarni
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from drakvuf_auto.config import DrakvufAutoConfig
from drakvuf_auto.diagnostics import DiagnosticResult
from drakvuf_auto.state import InstallerState


def generate_deployment_report(
    config: DrakvufAutoConfig,
    state: InstallerState,
    diag: DiagnosticResult,
    output_dir: Path
) -> Path:
    """Generate a comprehensive Markdown report summarizing the deployment."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / "deployment_summary.md"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    content = f"""# DRAKVUF Sandbox Deployment Summary Report
**Generated:** {timestamp}  
**Architect:** Nitiraj Kulkarni  
**Status:** {"Operational" if not state.reboot_pending else "Awaiting Reboot"}

---

## 1. Host Infrastructure
- **Processor:** {diag.cpu_model} ({diag.cpu_cores} cores)
- **Virtualization:** Intel VT-x ({diag.has_vmx}), EPT ({diag.has_ept})
- **Physical Memory:** {diag.total_ram_gb} GB
- **Operating System:** {diag.os_distro} {diag.os_release} (Kernel: {diag.kernel_version})
- **Hypervisor Status:** {"Xen Dom0 Active" if diag.is_xen_active else "Standard Linux"}

---

## 2. Xen Hypervisor Configuration
- **Xen Version:** {config.xen.version}
- **Dom0 Pinned Memory:** {config.hardware.dom0_memory_mb} MB
- **Dom0 Pinned vCPUs:** {config.hardware.dom0_max_vcpus}
- **GRUB Boot Parameters:** `{config.xen.grub_cmdline}`

---

## 3. Analysis Guest (Domain-U)
- **VM Domain Name:** `{config.guest.name}`
- **Operating System:** Windows 10/11 x64 (Agentless)
- **Memory Allocation:** {config.guest.memory_mb} MB
- **vCPUs:** {config.guest.vcpus}
- **Virtual Disk:** `{config.guest.disk_path}` ({config.guest.disk_size_gb} GB)
- **Network Bridge:** `{config.network.bridge}` (Subnet: {config.network.subnet})

---

## 4. Endpoints & Management
- **DrakWeb Dashboard:** [http://{config.services.web_bind}:{config.services.web_port}](http://{config.services.web_bind}:{config.services.web_port})
- **LibVMI Profiles:** `{config.symbols.profile_dir}`
- **State Checkpoint File:** `{output_dir.parent / "state" / "state.json"}`
- **Diagnostics Tool:** `sudo ./diagnose.sh`
- **Repair Tool:** `sudo ./repair.sh`

---
*Report generated automatically by drakvuf-auto-installer.*
"""
    report_file.write_text(content, encoding="utf-8")

    # Also save JSON format
    json_file = output_dir / "deployment_summary.json"
    json_data = {
        "timestamp": timestamp,
        "author": "Nitiraj Kulkarni",
        "host": {
            "cpu": diag.cpu_model,
            "ram_gb": diag.total_ram_gb,
            "xen_active": diag.is_xen_active,
        },
        "guest": {
            "name": config.guest.name,
            "disk": str(config.guest.disk_path),
            "ram_mb": config.guest.memory_mb,
        },
        "endpoints": {
            "web": f"http://{config.services.web_bind}:{config.services.web_port}",
        }
    }
    json_file.write_text(json.dumps(json_data, indent=2), encoding="utf-8")

    return report_file
