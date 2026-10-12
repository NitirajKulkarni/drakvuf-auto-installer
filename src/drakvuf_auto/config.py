"""Configuration management for DRAKVUF Sandbox Auto-Installer.

Author: Nitiraj Kulkarni
"""

import os
import sys
from pathlib import Path
from typing import Optional, Union

# Use standard library tomllib if Python 3.11+, else tomli fallback
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        import toml as tomllib  # type: ignore

from pydantic import BaseModel, Field, field_validator


class InstallationConfig(BaseModel):
    drakvuf_root: Path = Field(default=Path("/opt/drakvuf"))
    drakvuf_sandbox_root: Path = Field(default=Path("/opt/drakvuf-sandbox"))
    non_interactive: bool = True
    auto_repair: bool = True
    max_repair_attempts: int = Field(default=3, ge=1, le=10)


class HardwareConfig(BaseModel):
    min_ram_gb: int = Field(default=8, ge=4)
    dom0_memory_mb: int = Field(default=4096, ge=2048)
    dom0_max_vcpus: int = Field(default=2, ge=1)
    force_intel_ept: bool = True


class XenConfig(BaseModel):
    version: str = "4.19.2"
    source_url: str = "https://downloads.xenproject.org/release/xen/4.19.2/xen-4.19.2.tar.gz"
    grub_cmdline: str = (
        "dom0_mem=4096M,max:4096M dom0_max_vcpus=2 dom0_vcpus_pin=1 force-ept=1 "
        "ept=ad=0 hap_1gb=0 hap_2mb=0 altp2m=1 hpet=legacy-replacement smt=0 spec-ctrl=gds-mit=no"
    )
    allow_auto_reboot: bool = True


class DrakvufEngineConfig(BaseModel):
    repo: str = "https://github.com/tklengyel/drakvuf.git"
    sandbox_repo: str = "https://github.com/CERT-Polska/drakvuf-sandbox.git"
    install_mode: str = "source"

    @field_validator("install_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v.lower() not in ("source", "prebuilt"):
            raise ValueError("install_mode must be 'source' or 'prebuilt'")
        return v.lower()


class GuestConfig(BaseModel):
    name: str = "win10-drakvuf"
    windows_edition: str = "win10_eval"
    auto_download_iso: bool = True
    iso_path: str = ""
    eval_iso_url: str = ""
    disk_path: Path = Field(default=Path("/var/lib/drakvuf/images/win10.img"))
    disk_size_gb: int = Field(default=40, ge=20)
    memory_mb: int = Field(default=4096, ge=2048)
    vcpus: int = Field(default=2, ge=1)
    unattended: bool = True
    vnc_port: int = Field(default=5900, ge=1024, le=65535)


class NetworkConfig(BaseModel):
    bridge: str = "xenbr0"
    subnet: str = "192.168.100.0/24"
    gateway: str = "192.168.100.1"
    dhcp_start: str = "192.168.100.100"
    dhcp_end: str = "192.168.100.200"


class ServicesConfig(BaseModel):
    web_bind: str = "127.0.0.1"
    web_port: int = Field(default=6300, ge=1, le=65535)
    redis_port: int = Field(default=6379, ge=1, le=65535)
    minio_port: int = Field(default=9000, ge=1, le=65535)
    minio_console_port: int = Field(default=9001, ge=1, le=65535)


class SymbolsConfig(BaseModel):
    symbol_server_url: str = "https://msdl.microsoft.com/download/symbols"
    profile_dir: Path = Field(default=Path("/etc/libvmi"))


class DrakvufAutoConfig(BaseModel):
    installation: InstallationConfig = Field(default_factory=InstallationConfig)
    hardware: HardwareConfig = Field(default_factory=HardwareConfig)
    xen: XenConfig = Field(default_factory=XenConfig)
    drakvuf: DrakvufEngineConfig = Field(default_factory=DrakvufEngineConfig)
    guest: GuestConfig = Field(default_factory=GuestConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    services: ServicesConfig = Field(default_factory=ServicesConfig)
    symbols: SymbolsConfig = Field(default_factory=SymbolsConfig)


def load_config(config_path: Union[str, Path]) -> DrakvufAutoConfig:
    """Load and validate configuration from TOML file."""
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "rb") as f:
        data = tomllib.load(f)

    return DrakvufAutoConfig.model_validate(data)
