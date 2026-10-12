<div align="center">

# 🐉 DRAKVUF Sandbox Universal Automated Installer & VMI Orchestrator

**A self-healing, state-persisted, reboot-surviving automated deployment engine for agentless malware analysis via Xen Dom0 Virtual Machine Introspection.**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Debian: 12 Bookworm](https://img.shields.io/badge/Debian-12%20Bookworm-D70A53?logo=debian&logoColor=white)](https://www.debian.org/)
[![Ubuntu: 22.04 LTS](https://img.shields.io/badge/Ubuntu-22.04%20LTS-E95420?logo=ubuntu&logoColor=white)](https://ubuntu.com/)
[![Hypervisor: Xen 4.19 Dom0](https://img.shields.io/badge/Hypervisor-Xen%204.19%20Dom0-005B94?logo=xen&logoColor=white)](https://xenproject.org/)
[![Introspection: Agentless VMI](https://img.shields.io/badge/Introspection-Agentless%20VMI-red.svg)](https://drakvuf.com/)
[![CPU: Intel VT--x + EPT](https://img.shields.io/badge/Hardware-Intel%20VT--x%20%2B%20EPT-0071C5?logo=intel&logoColor=white)](https://ark.intel.com/)

**Author & Maintainer:** [**Nitiraj V. Kulkarni — AI Safety & Cybersecurity Researcher**](https://nitirajkulkarni.in/)  
[![Website](https://img.shields.io/badge/Website-nitirajkulkarni.in-0078D6?style=flat&logo=googlechrome&logoColor=white)](https://nitirajkulkarni.in/)
[![Google Scholar](https://img.shields.io/badge/Google_Scholar-Citations-4285F4?style=flat&logo=googlescholar&logoColor=white)](https://scholar.google.com/citations?user=yfHyH68AAAAJ)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/nitirajkulkarni)
[![GitHub](https://img.shields.io/badge/GitHub-NitirajKulkarni-181717?style=flat&logo=github&logoColor=white)](https://github.com/NitirajKulkarni)

---

### ⚡ Zero to DRAKVUF Sandbox in One Command

```bash
git clone https://github.com/NitirajKulkarni/drakvuf-auto-installer.git
cd drakvuf-auto-installer && chmod +x *.sh
sudo ./install.sh
```

</div>

---

## 📖 Overview

In modern threat intelligence and malware engineering, analyzing sophisticated rootkits, loaders, and ransomware requires an analysis environment that cannot be detected or evaded. Traditional dynamic sandboxes (such as Cuckoo or CAPEv2) rely on **in-guest agents** (`agent.py`) and API hooking DLLs injected into target processes. Advanced evasive malware routinely detects these user-space artifacts, unhooks Win32 APIs, bypasses monitoring, or terminates early.

[DRAKVUF Sandbox](https://github.com/CERT-Polska/drakvuf-sandbox) solves this evasion problem through **Virtual Machine Introspection (VMI)** built on the **Xen Project Hypervisor** and Tamas K. Lengyel’s [DRAKVUF engine](https://drakvuf.com/). Because monitoring occurs entirely from outside the guest virtual machine at the hypervisor microkernel layer, the guest OS contains **zero monitoring software, zero injected DLLs, and zero open communication ports**.

However, setting up DRAKVUF Sandbox manually is notoriously difficult. As warned by CERT Polska: *"Here be dragons 🐉. Maintaining your own sandbox is a difficult task and this project uses technology that is not user-friendly."*

### Challenges Solved by `drakvuf-auto-installer`:
1. ⚙️ **Bare-Metal Microkernel Boot:** Automatically compiles Xen 4.19, patches upstream submodules (Tianocore OVMF git credential bug), tunes `/etc/default/grub` with optimal EPT/Altp2m parameters, and reboots the host into **Xen Dom0**.
2. 🔄 **Reboot-Surviving State Engine:** Uses an atomic state machine with a temporary systemd handshake unit (`drakvuf-installer-resume.service`) to seamlessly resume installation across the mandatory host reboot.
3. 🔬 **Pre-Flight Hardware Qualification:** Deeply verifies Intel CPU extensions (`vmx`, `ept`, `altp2m`), memory limits, and bare-metal environments before altering host boot configurations.
4. 🧬 **Automated Microsoft PDB Symbol Synthesis:** Eliminates tedious manual symbol dumping by extracting kernel GUIDs via LibVMI, pulling official `.pdb` files from Microsoft Public Symbol Server, and generating LibVMI JSON profiles.
5. 🪟 **Agentless Windows Guest Automation:** Uses a headless `autounattend.xml` response file to automatically partition and configure Windows 10/11 HVM domains with OOBE network bypass and Defender remediation.
6. 🌐 **Production Microservices Stack:** Deploys Redis queues, MinIO S3 object storage, and DrakWeb interface as monitored systemd services.

---

## 🏗️ Architectural Topology

```
+---------------------------------------------------------------------------------------------------+
|                                      Bare-Metal Host Hardware                                     |
|                              (Strictly Intel VT-x + EPT + Altp2m)                                 |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                       Xen Hypervisor 4.19                                         |
|                                    (Bare-Metal Type-1 Microkernel)                                |
+-------------------------------------------------+-------------------------------------------------+
                         |                                                         |
                         v                                                         v
+-------------------------------------------------+       +-----------------------------------------+
|              Domain-0 (Linux Dom0)              |       |         Domain-U (Windows Guest)        |
|-------------------------------------------------|       |-----------------------------------------|
| • DrakCore (Task Queue & Dispatcher)            |       | • 100% Vanilla Windows 10 / 11          |
| • DrakWeb (REST API & Web UI Dashboard)         |       | • ZERO agent.py or scripts in guest     |
| • DRAKVUF Engine & Injector Toolstack           |       | • ZERO injected DLLs or hooks           |
| • LibVMI Introspection Kernel Interface         |       | • Trapped via Intel Hardware Traps:     |
| • Automated Microsoft PDB Symbol Synthesizer    |       |   - EPT Violations                      |
| • xenbr0 Virtual Network Bridge                 |       |   - Altp2m Shadow Page Switching        |
+-------------------------------------------------+       +-----------------------------------------+
```

---

## 🚀 Quick Start Guide

### 1. Hardware Qualification Check
Before modifying any bootloader parameters, run the built-in diagnostic probe to verify your CPU and virtualization extensions:
```bash
sudo ./diagnose.sh
```

### 2. Execute Full Installation
Run the master installer. It will automatically build Xen, configure GRUB, schedule post-reboot auto-resume, and reboot into Xen Dom0:
```bash
sudo ./install.sh
```

> [!NOTE]
> During **Phase 1**, the installer updates GRUB with hypervisor flags (`force-ept=1 altp2m=1 dom0_mem=4096M`) and prompts/initiates a host reboot. Upon rebooting into Xen Dom0, the systemd resume unit automatically triggers `install.sh --resume` to continue with engine compilation and Windows guest deployment!

### 3. Check Real-Time Deployment Status
Inspect phase completion, checkpoint timestamps, and hypervisor status:
```bash
sudo ./status.sh
```

### 4. Automated Healing & Diagnostics
If a service or Xen kernel module is unloaded after a maintenance event:
```bash
sudo ./repair.sh
```

### 5. Clean Reinstallation (Full Reset)
To clear state and re-provision from scratch:
```bash
sudo ./clean-install.sh
```

---

## 🪟 100% Agentless Windows Guest & Symbol Profiling

Unlike agent-based sandboxes where Windows must run custom scripts and background daemons, DRAKVUF guest VMs are completely unadorned:

```
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│ Genuine Microsoft      │      │ Automated Answer File  │      │ Xen HVM Domain Boot    │
│ Windows 10 Eval ISO    │ ───► │ autounattend.xml       │ ───► │ xl create win10.cfg    │
│ (22H2 Recommended)     │      │ OOBE Bypass + Defender │      │ Raw Disk: 40 GB        │
└────────────────────────┘      └────────────────────────┘      └───────────┬────────────┘
                                                                            │
┌────────────────────────┐      ┌────────────────────────┐                  ▼
│ Ready for Malware VMI  │      │ LibVMI JSON Profile    │      ┌────────────────────────┐
│ Zero Hooks / Pure Traps│ ◄─── │ /etc/libvmi/win10.json │ ◄─── │ Microsoft Symbol Server│
│ DrakWeb UI: Port 6300  │      │ Offsets: _EPROCESS/PEB │      │ Fetches .pdb via GUID  │
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘
```

1. **Unattended Deployment:** Automated Windows 10/11 HVM setup with automated disk partitioning, admin user setup, and OOBE bypass (`BypassNRO`).
2. **Kernel GUID Extraction:** Uses LibVMI CLI tools (`vmi-win-guid`) to probe the exact kernel signature directly from guest memory.
3. **Microsoft Public Symbol Retrieval:** Downloads matching debug symbols (`ntoskrnl.pdb`, `ntdll.pdb`, `win32k.pdb`) from Microsoft's public symbol servers with exponential backoff and local caching.
4. **LibVMI Profile Synthesis:** Assembles structure offsets (`_EPROCESS`, `_ETHREAD`, system calls) into `/etc/libvmi/win10.json` and verifies live introspection via `vmi-process-list`.

---

## 📋 System Requirements & Compatibility

| Component | Minimum Requirement | Recommended |
| :--- | :--- | :--- |
| **Processor** | Intel CPU with **VT-x** and **EPT** | Intel Core i7/i9 (10th Gen+) or Intel Xeon |
| **Architecture** | 64-bit x86_64 Bare-Metal | Physical Bare-Metal Server / Workstation |
| **Memory** | 8 GB Physical RAM (4 GB Dom0 + 4 GB Guest) | 16 GB - 32 GB RAM |
| **Storage** | 50 GB Free NVMe/SSD Storage | 100 GB+ NVMe SSD |
| **Host OS** | Debian 12 (Bookworm) / Ubuntu 22.04 LTS | Clean minimal server installation |
| **Bootloader** | GRUB2 | Standard GRUB |

> [!WARNING]
> **Strict Hardware Limitation:** DRAKVUF **strictly requires an Intel processor**. AMD processors (SVM) do not support the Altp2m shadow page table mechanism required for stealthy hardware introspection. Standard cloud virtualization instances (AWS EC2, Google Cloud, Azure) are not supported due to missing nested EPT support.

---

## 📊 Comparative Architecture: CAPEv2 vs. DRAKVUF

| Architectural Dimension | CAPEv2 Sandbox | DRAKVUF Sandbox |
| :--- | :--- | :--- |
| **Monitoring Paradigm** | In-guest Agent (`agent.py`) + Injected DLLs | **Agentless VMI** (Intel EPT/Altp2m Shadow Pages) |
| **Hypervisor** | KVM / QEMU via `libvirt` | **Xen Project Hypervisor** (Bare-Metal Type-1 Dom0) |
| **Host Microkernel Reboot** | Zero reboot required | **Mandatory host reboot** into Xen Dom0 |
| **Hardware Compatibility**| Intel, AMD, Nested Cloud VMs (AWS/GCP/Azure) | **Strictly Intel VT-x + EPT (Bare-metal)** |
| **Malware Evasion Resistance** | Moderate (vulnerable to anti-hooking & unhooking) | **Maximum** (malware sees unmodified memory) |
| **Kernel Symbols** | Not needed by host | **Strictly requires exact Microsoft PDB symbols** |
| **Deployment Automation** | `capev2-auto-installer` | `drakvuf-auto-installer` |

---

## 🛠️ CLI Operations & Toolset

```bash
# Display phase status, checkpoints, and reboot tracking
sudo ./status.sh

# Run deep pre-flight hardware and hypervisor diagnostics
sudo ./diagnose.sh

# Automatically repair Xen modules, library caches, or service state
sudo ./repair.sh

# Revert bootloader default to standard Ubuntu if needed
sudo ./repair.sh --restore-ubuntu-boot

# Re-enable Xen Hypervisor as default boot entry
sudo ./repair.sh --enable-xen-boot

# Reset deployment state and re-provision from scratch
sudo ./clean-install.sh

# Gracefully teardown services, bridges, and configurations
sudo ./uninstall.sh
```

---

## 🛡️ Host Integrity, Zero Data-Loss Guarantee & Safe Recovery

This deployment suite adheres to strict safety principles: **it never touches personal partitions, modifies existing user files, or reformats storage drives.**

### Understanding Microkernel Dual-Boot Architecture
1. Phase 1 registers the Xen Hypervisor microkernel alongside your existing Linux kernel in GRUB.
2. All regular Linux kernels remain fully installed and accessible under **"Advanced options for Ubuntu"**.
3. Modern Ubuntu releases (24.04 / 26.04) utilize **Dracut** for early-stage initramfs generation. If Dracut's host-only configuration encounters missing storage drivers when booting under Xen Dom0 (e.g., `dracut-initqueue: timeout`), **your host system and data are 100% intact**.

### Emergency Recovery (Bypassing Xen)
If your machine ever pauses or halts during Xen Dom0 boot:
1. Power cycle or reboot your system.
2. When the GRUB menu appears, select:
   ```text
   Advanced options for Ubuntu
     └── Ubuntu, with Linux <kernel-version>-generic   <-- (Select normal Linux kernel)
   ```
3. Your machine boots cleanly into standard Ubuntu with complete desktop and data access.
4. Open a terminal and run the automated repair utility:
   ```bash
   cd drakvuf-auto-installer
   git pull
   sudo ./repair.sh
   ```
   *This automatically creates `/etc/dracut.conf.d/xen.conf`, injects `xen-blkfront`, `nvme`, and `ahci` storage controller modules, and regenerates ramdisk images.*

### Switching Default Bootloader Entry
You can toggle your default boot entry at any time:
```bash
# Revert default boot to standard Ubuntu Linux
sudo ./repair.sh --restore-ubuntu-boot

# Re-enable Xen Hypervisor as default boot entry
sudo ./repair.sh --enable-xen-boot
```

---

## 👤 Author & Maintainer

**Nitiraj V. Kulkarni**  
*AI Safety & Cybersecurity Researcher*  
- **Website:** [https://nitirajkulkarni.in](https://nitirajkulkarni.in/)  
- **Google Scholar:** [Citations & Publications](https://scholar.google.com/citations?user=yfHyH68AAAAJ)  
- **LinkedIn:** [linkedin.com/in/nitirajkulkarni](https://www.linkedin.com/in/nitirajkulkarni)  
- **GitHub:** [@NitirajKulkarni](https://github.com/NitirajKulkarni)

---

## 🤝 Acknowledgments & Upstream Projects

This automated deployment framework builds upon the groundbreaking work of:
- **Tamas K. Lengyel** — Creator of the [DRAKVUF engine](https://drakvuf.com/) and LibVMI.
- **CERT Polska** — Authors and maintainers of [DRAKVUF Sandbox](https://github.com/CERT-Polska/drakvuf-sandbox).
- **The Xen Project** — The high-performance, open-source Type-1 hypervisor team.

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.  
See the [LICENSE](LICENSE) file for complete details.
