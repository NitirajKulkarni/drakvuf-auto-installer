# DRAKVUF Sandbox Automated Installer (`drakvuf-auto-installer`)

[![Platform](https://img.shields.io/badge/Platform-Debian%2012%20%7C%20Ubuntu%2022.04%20LTS-orange.svg)](#requirements)
[![Virtualization](https://img.shields.io/badge/Hypervisor-Xen%204.19%20(Dom0)-blue.svg)](#architecture)
[![Introspection](https://img.shields.io/badge/Engine-DRAKVUF%20%7C%20LibVMI-green.svg)](#architecture)
[![Architecture](https://img.shields.io/badge/Analysis-Agentless%20VMI-red.svg)](#how-it-works)
[![Author](https://img.shields.io/badge/Author-Nitiraj%20Kulkarni-purple.svg)](#author--credits)

**`drakvuf-auto-installer`** is a zero-touch, state-persisted, reboot-surviving automation framework for deploying **[DRAKVUF Sandbox](https://github.com/CERT-Polska/drakvuf-sandbox)**—the premier agentless malware analysis system built on **Virtual Machine Introspection (VMI)** and the **Xen Project Hypervisor**.

Developed by **Nitiraj Kulkarni**, this installer replaces hours of fragile manual compilation, hypervisor configuration, GRUB tuning, and Microsoft PDB symbol extraction with a deterministic, single-command deployment pipeline.

---

## 🌟 Why DRAKVUF Sandbox?

Traditional malware sandboxes (like Cuckoo or CAPEv2) rely on **in-guest agents** (`agent.py`) and API hooking DLLs injected into running Windows processes. Modern evasion-aware malware and rootkits can easily detect these artifacts, unhook APIs, terminate the agent, or evade analysis entirely.

**DRAKVUF Sandbox changes the paradigm:**
- **100% Agentless:** Zero software, scripts, or hooks exist inside the guest operating system.
- **Hardware-Enforced Introspection:** Leverages **Intel VT-x**, **Extended Page Tables (EPT)**, and **Alternate Physical-to-Machine (Altp2m)** shadow page tables to trap instructions from outside the VM.
- **Undetectable Traps:** Execution is intercepted directly from the hypervisor microkernel; malware reading its own memory sees completely clean, unmodified code pages.

---

## 🏗️ System Architecture

```
                                  +---------------------------------------+
                                  |         Bare-Metal Hardware           |
                                  |       (Intel VT-x + EPT Only)         |
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |         Xen Hypervisor 4.19           |
                                  |     (Type-1 Microkernel Core)         |
                                  +---------+-------------------+---------+
                                            |                   |
                                            v                   v
             +--------------------------------------+   +--------------------------------------+
             |         Domain-0 (Linux Dom0)        |   |         Domain-U (Windows Guest)     |
             |--------------------------------------|   |--------------------------------------|
             | • DrakCore (Queue & Dispatcher)      |   | • Completely Vanilla Windows OS      |
             | • DrakWeb (Web Dashboard & API)      |   | • NO agent.py                        |
             | • DRAKVUF Engine & Injector          |   | • NO injected DLLs                   |
             | • LibVMI Introspection Interface    |   | • Trapped via EPT & Altp2m Traps     |
             | • Automated PDB Symbol Engine        |   +--------------------------------------+
             +--------------------------------------+
```

---

## 🚀 Key Features

- **Reboot-Surviving State Machine:** Automatically transitions the host Linux OS into a Xen Dom0 microkernel, provisions a one-shot systemd resume unit, reboots, and seamlessly resumes installation without manual intervention.
- **Pre-Flight Hardware Qualification:** Deep validation of Intel CPU features (`vmx`, `ept`, `altp2m`), RAM allocation (Dom0 memory pinning), and cloud hypervisor detection to prevent failed deployments before modifying system files.
- **Automated Xen 4.19 Toolstack:** Compiles and packages Xen with embedded upstream hotfixes (e.g., Tianocore OVMF submodule credential patches).
- **Zero-Touch Windows Provisioning:** Headless deployment of Windows 10/11 HVM guests with automated partitioning, OOBE network bypass (`BypassNRO`), and Defender remediation via `autounattend.xml`.
- **Microsoft PDB Symbol Synthesizer:** Automatically queries guest kernel GUIDs via LibVMI, retrieves exact `.pdb` debug symbols from the Microsoft Symbol Server, and synthesizes LibVMI JSON profiles.
- **Microservices Deployment:** Provisions Redis task queues, MinIO S3-compatible artifact storage, and DrakWeb interface as persistent systemd services.
- **Self-Healing Diagnostics:** Includes standalone diagnostic (`./diagnose.sh`) and repair (`./repair.sh`) tools for Xen modules, networking, and introspection checks.

---

## 📋 System Requirements

| Component | Minimum Requirement | Recommended |
| :--- | :--- | :--- |
| **Processor** | Intel CPU with **VT-x** and **EPT** | Modern multi-core Intel Core i7/i9 or Xeon |
| **Architecture** | x86_64 bare-metal | Physical hardware (Cloud VMs generally lack nested EPT) |
| **Memory** | 8 GB RAM (4 GB Dom0 + 4 GB Guest) | 16 GB+ RAM |
| **Storage** | 50 GB free disk space | NVMe SSD storage |
| **Host OS** | Debian 12 (Bookworm) / Ubuntu 22.04 LTS | Clean server installation |
| **Bootloader** | GRUB2 | Standard GRUB |

> [!IMPORTANT]
> DRAKVUF **strictly requires an Intel processor**. AMD processors (SVM) do not support the Altp2m shadow page table mechanism required for agentless introspection. Standard cloud instances (AWS EC2, Google Cloud, Azure) are not supported due to suppressed nested EPT extensions.

---

## ⚡ Quickstart

### 1. Clone the Repository
```bash
git clone https://github.com/NitirajKulkarni/drakvuf-auto-installer.git
cd drakvuf-auto-installer
```

### 2. Verify Hardware Compatibility
Run the pre-flight diagnostic suite to ensure your CPU and environment meet all VMI requirements:
```bash
sudo ./diagnose.sh
```

### 3. Review Configuration
Inspect `config.toml` to customize RAM allocation, network subnets, or Windows ISO paths (defaults are production-ready):
```bash
nano config.toml
```

### 4. Execute Installation
```bash
sudo ./install.sh
```
*The installer will configure Xen, update GRUB, reboot your machine into Xen Dom0, and automatically resume installation to deploy the guest VM, symbols, and DrakWeb interface.*

---

## 🛠️ Management & Operations

```bash
# Check status of phases, checkpoints, and Xen Dom0
sudo ./status.sh

# Run deep diagnostics on hypervisor, LibVMI, and storage
sudo ./diagnose.sh

# Automatically remediate Xen modules or service issues
sudo ./repair.sh

# Reset deployment state and perform a clean install
sudo ./clean-install.sh

# Safely teardown services, bridges, and configurations
sudo ./uninstall.sh
```

---

## 📊 Comparison: CAPEv2 vs. DRAKVUF Sandbox

| Feature | CAPEv2 Sandbox | DRAKVUF Sandbox |
| :--- | :--- | :--- |
| **Detection Method** | Guest agent (`agent.py`) & injected DLLs | **Agentless VMI** (Intel EPT/Altp2m Traps) |
| **Hypervisor** | KVM / QEMU via `libvirt` | **Xen Project Hypervisor** (Type-1 Dom0) |
| **Host Reboot** | Zero reboot required | **Mandatory reboot** into Xen Dom0 |
| **Hardware Compatibility**| Intel, AMD, Nested Cloud VMs | **Strictly Intel VT-x + EPT (Bare-metal)** |
| **Stealth Level** | Moderate (vulnerable to anti-hooking/direct syscalls) | **Maximum** (invisible to guest malware) |
| **Symbol Dependency** | Not required | **Strictly requires exact Microsoft PDB symbols** |

---

## 👤 Author & Credits

Designed and maintained by **[Nitiraj Kulkarni](https://github.com/NitirajKulkarni)**.

Special thanks to:
- **Tamas K. Lengyel** for creating the [DRAKVUF engine](https://drakvuf.com/) and LibVMI.
- **CERT Polska** for maintaining [DRAKVUF Sandbox](https://github.com/CERT-Polska/drakvuf-sandbox).

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.
