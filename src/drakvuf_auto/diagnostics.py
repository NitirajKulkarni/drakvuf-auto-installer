"""Pre-flight hardware, hypervisor, and system diagnostic probes.

Author: Nitiraj Kulkarni
"""

import json
import logging
import os
import platform
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from drakvuf_auto.command import command_exists, run_command
from drakvuf_auto.exceptions import HardwareIncompatibleError, PreFlightCheckError

logger = logging.getLogger("drakvuf_auto.diagnostics")


@dataclass
class DiagnosticResult:
    is_intel: bool = False
    has_vmx: bool = False
    has_ept: bool = False
    cpu_model: str = "Unknown"
    cpu_cores: int = 0
    total_ram_gb: float = 0.0
    free_disk_gb: float = 0.0
    os_distro: str = "Unknown"
    os_release: str = "Unknown"
    kernel_version: str = "Unknown"
    is_xen_active: bool = False
    xen_version: str = "None"
    dom0_active: bool = False
    cloud_provider: str = "Bare-Metal / Local"
    issues: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.warnings is None:
            self.warnings = []

    @property
    def passed(self) -> bool:
        return len(self.issues) == 0


class SystemDiagnostics:
    """Probes the host system to determine readiness for DRAKVUF Sandbox."""

    def __init__(self, min_ram_gb: int = 8, min_disk_gb: int = 40):
        self.min_ram_gb = min_ram_gb
        self.min_disk_gb = min_disk_gb

    def run_all_checks(self) -> DiagnosticResult:
        result = DiagnosticResult()

        self._check_cpu(result)
        self._check_memory(result)
        self._check_storage(result)
        self._check_os(result)
        self._check_xen(result)
        self._check_cloud_environment(result)

        return result

    def _check_cpu(self, result: DiagnosticResult) -> None:
        """Inspect /proc/cpuinfo for Intel VT-x and EPT virtualization flags."""
        cpuinfo_path = Path("/proc/cpuinfo")
        if not cpuinfo_path.exists():
            result.issues.append("Unable to read /proc/cpuinfo (non-Linux environment or restricted)")
            return

        try:
            content = cpuinfo_path.read_text(encoding="utf-8")
        except Exception as e:
            result.issues.append(f"Failed to read /proc/cpuinfo: {e}")
            return

        # Check vendor
        is_intel = "GenuineIntel" in content
        result.is_intel = is_intel

        # Extract model
        model_match = re.search(r"model name\s+:\s+(.+)", content)
        if model_match:
            result.cpu_model = model_match.group(1).strip()

        # Count cores
        result.cpu_cores = len(re.findall(r"^processor\s+:", content, re.MULTILINE))

        # Check flags
        flags_match = re.search(r"flags\s+:\s+(.+)", content)
        flags = flags_match.group(1).split() if flags_match else []

        result.has_vmx = "vmx" in flags
        result.has_ept = "ept" in flags

        if not is_intel:
            result.issues.append(
                "DRAKVUF requires an Intel processor. AMD processors (SVM) do NOT support "
                "the necessary Altp2m shadow page table mechanism for agentless VMI."
            )
        elif not result.has_vmx:
            result.issues.append("CPU does not support Intel VT-x (vmx flag missing in /proc/cpuinfo).")
        elif not result.has_ept:
            result.issues.append(
                "CPU lacks Extended Page Tables (EPT) support. DRAKVUF requires EPT for memory virtualization."
            )

    def _check_memory(self, result: DiagnosticResult) -> None:
        """Check available physical RAM."""
        meminfo = Path("/proc/meminfo")
        if meminfo.exists():
            try:
                for line in meminfo.read_text().splitlines():
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        result.total_ram_gb = round(kb / (1024 * 1024), 2)
                        break
            except Exception:
                pass

        if result.total_ram_gb > 0 and result.total_ram_gb < self.min_ram_gb:
            result.warnings.append(
                f"Host RAM ({result.total_ram_gb} GB) is below recommended minimum ({self.min_ram_gb} GB). "
                "DRAKVUF requires at least 4 GB pinned to Dom0 and 4 GB for the Windows guest."
            )

    def _check_storage(self, result: DiagnosticResult) -> None:
        """Check available disk space in root and /var/lib."""
        try:
            stat = shutil.disk_usage("/var" if os.path.exists("/var") else "/")
            result.free_disk_gb = round(stat.free / (1024**3), 2)
            if result.free_disk_gb < self.min_disk_gb:
                result.issues.append(
                    f"Insufficient free disk space ({result.free_disk_gb} GB available, "
                    f"{self.min_disk_gb} GB required for Xen, guest image, and symbols)."
                )
        except Exception:
            pass

    def _check_os(self, result: DiagnosticResult) -> None:
        """Check Linux distribution and kernel version."""
        result.kernel_version = platform.release()
        os_release = Path("/etc/os-release")
        if os_release.exists():
            try:
                data = {}
                for line in os_release.read_text().splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        data[k.strip()] = v.strip().strip('"')
                result.os_distro = data.get("NAME", "Linux")
                result.os_release = data.get("VERSION_ID", "")
            except Exception:
                pass

    def _check_xen(self, result: DiagnosticResult) -> None:
        """Check if Xen hypervisor is currently running as Dom0."""
        # 1. Check xen-detect binary
        if command_exists("xen-detect"):
            try:
                cmd = run_command("xen-detect", stream=False, check=False)
                if "Running in PV context on Xen" in cmd.stdout:
                    result.is_xen_active = True
                    match = re.search(r"Xen V([\d\.]+)", cmd.stdout)
                    if match:
                        result.xen_version = match.group(1)
            except Exception:
                pass

        # 2. Check /sys/hypervisor/type
        hyp_type = Path("/sys/hypervisor/type")
        if hyp_type.exists():
            try:
                if hyp_type.read_text().strip() == "xen":
                    result.is_xen_active = True
            except Exception:
                pass

        # 3. Check Domain-0 status via xl list
        if result.is_xen_active and command_exists("xl"):
            try:
                cmd = run_command("xl list", stream=False, check=False)
                if "Domain-0" in cmd.stdout:
                    result.dom0_active = True
            except Exception:
                pass

    def _check_cloud_environment(self, result: DiagnosticResult) -> None:
        """Detect cloud instances where nested VT-x/EPT is restricted."""
        dmi_path = Path("/sys/class/dmi/id/sys_vendor")
        if dmi_path.exists():
            try:
                vendor = dmi_path.read_text().strip().lower()
                if "amazon" in vendor:
                    result.cloud_provider = "AWS EC2"
                elif "google" in vendor:
                    result.cloud_provider = "Google Cloud"
                elif "microsoft" in vendor:
                    result.cloud_provider = "Microsoft Azure"
            except Exception:
                pass

        if result.cloud_provider != "Bare-Metal / Local":
            result.warnings.append(
                f"Detected cloud environment: {result.cloud_provider}. "
                "DRAKVUF Sandbox typically requires bare-metal hardware. Standard cloud hypervisors "
                "do not expose Intel Altp2m/EPT nested virtualization."
            )
