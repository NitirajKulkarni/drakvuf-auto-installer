# DRAKVUF Sandbox Automated Installer (`drakvuf-auto-installer`)
## Comprehensive Architectural Specification and Implementation Master Plan
**Author:** Nitiraj Kulkarni  
**Repository:** `drakvuf-auto-installer`  
**Target Environment:** Debian 12 (Bookworm) / Ubuntu 22.04 LTS (Jammy) | Intel VT-x + EPT  
**Classification:** Production Infrastructure Automation / Malware Analysis Engineering  

---

## 1. Executive Summary & Problem Space

### 1.1 The Challenge
[DRAKVUF Sandbox](https://github.com/CERT-Polska/drakvuf-sandbox) is the premier open-source, agentless malware analysis system in cybersecurity. Built upon Tamas K. Lengyel’s [DRAKVUF engine](https://drakvuf.com/) and LibVMI, it monitors malware using **Virtual Machine Introspection (VMI)** directly at the hypervisor level. 

Because monitoring is performed from the outside using hardware virtualization extensions (Intel VT-x, Extended Page Tables / EPT, and Alternate Physical-to-Machine / Altp2m shadow page tables), it is virtually invisible to in-guest malware. There are no agents, no injected DLLs, and no open communication ports inside the guest operating system.

However, deploying DRAKVUF Sandbox manually has one of the steepest learning curves in system security:
1. **Host Microkernel Transition:** Requires compiling and running the **Xen Project Hypervisor**, demoting the host Linux OS into a privileged virtual machine (**Dom0**).
2. **Strict Hardware Dependencies:** Demands explicit Intel VT-x with EPT features; fails silently on AMD CPUs or standard cloud virtualization (AWS, Azure, GCP) that do not expose Altp2m/EPT nested paging.
3. **Mandatory Host Reboot:** Unlike standard KVM sandboxes (like CAPEv2), the host machine must be rebooted into the Xen hypervisor before any guest VM or VMI tool can run.
4. **PDB Debug Symbol Synthesis:** The hypervisor cannot read guest memory structures without exact Microsoft PDB debugging symbols (`ntoskrnl.exe`, `win32k.sys`, `ntdll.dll`). Any mismatch between Windows build versions and LibVMI JSON profiles renders analysis dead.
5. **Multi-Service Orchestration:** Requires integrating Xen toolstacks (`xl`), `drakcore`, `drakweb`, Redis queues, and MinIO S3 object storage into a cohesive systemd service pipeline.

### 1.2 The Mission
To build **`drakvuf-auto-installer`**: a zero-touch, deterministic, state-persisted, reboot-surviving CLI automation tool that provisions a production-ready DRAKVUF Sandbox from a clean Linux installation to full malware analysis readiness with a single command.

---

## 2. Core Architectural Pillars

```
+---------------------------------------------------------------------------------------------------+
|                                      drakvuf-auto CLI                                             |
|                               (Typer / Rich / Pydantic Core)                                      |
+---------------------------------+---------------------------------+-------------------------------+
                                  |                                 |
                                  v                                 v
                 +---------------------------------+ +-------------------------------+
                 |       State & Checkpoint        | |     Command & Process         |
                 |      Engine (Atomic JSON)       | |     Runner (Live Streaming)   |
                 +---------------------------------+ +-------------------------------+
                                  |
                                  v
+---------------------------------------------------------------------------------------------------+
|                                  Multi-Phase Execution Pipeline                                   |
+---------------------------------------------------------------------------------------------------+
|  Phase 0: Pre-Flight Diagnostics (Intel VT-x, EPT, Altp2m, Memory, Storage)                      |
|  Phase 1: Xen Hypervisor 4.19 Build & GRUB Cmdline Configuration                                  |
|  Phase 2: Reboot Orchestration & Systemd Auto-Resume Handshake                                    |
|  Phase 3: LibVMI & DRAKVUF Engine Compilation (llvm, meson, ninja)                                |
|  Phase 4: Network Bridge & Xen Virtualization Storage Provisioning                                |
|  Phase 5: Automated Windows 10 HVM Deployment (Unattended XML)                                    |
|  Phase 6: Kernel Symbol Extraction & LibVMI JSON Profile Synthesis                                |
|  Phase 7: DRAKVUF Sandbox Microservices (DrakCore, DrakWeb, Redis, MinIO)                         |
|  Phase 8: End-to-End Validation Run (pafish.exe / Benign Binary Verification)                      |
+---------------------------------------------------------------------------------------------------+
```

### Pillar 1: The Reboot-Surviving State Engine
Because Xen requires a system reboot to boot into Dom0, the installer cannot run in a single synchronous process.  
- We implement an **Atomic State Machine** (`state/state.json`) tracking each completed step and phase.
- Prior to rebooting in Phase 1, the installer writes a systemd unit (`/etc/systemd/system/drakvuf-installer-resume.service`).
- On reboot, systemd automatically executes `drakvuf-auto install --resume`, verifies Dom0 state (`xen-detect`, `xl list`), removes the resume service, and seamlessly proceeds to Phase 3.

### Pillar 2: Pre-Flight Hardware Qualification
Failing after hours of building Xen due to missing CPU extensions is unacceptable. Phase 0 performs deep CPU capability checks:
- Verifies Intel Vendor ID (`GenuineIntel`).
- Inspects `/proc/cpuinfo` for `vmx` and `ept`.
- Probes MSR registers or `/sys/module/kvm_intel/parameters/ept` to ensure Extended Page Tables and secondary processor execution controls support Altp2m.
- Validates RAM (minimum 8GB physical RAM; pins 4GB to Dom0, allocates remaining to guest VM).

### Pillar 3: Deterministic Tool & Engine Compilation
Xen and DRAKVUF evolve rapidly. Upstream distributions frequently suffer from broken submodules (e.g., Tianocore OVMF subhook Git credential bug in Xen 4.19).  
The installer embeds automated patch sets into `templates/patches/` to ensure builds complete deterministically without human intervention.

### Pillar 4: Automated Windows Symbol Extraction
Instead of relying on manual VNC clicks to prepare Windows and dump kernel binaries, the installer:
1. Spawns Windows HVM using an automated `autounattend.xml` response file.
2. Mounts the guest virtual disk or uses LibVMI CLI tools (`vmi-win-guid`, `vmi-win-offsets`) to query kernel version GUIDs.
3. Automatically fetches corresponding `.pdb` files directly from `https://msdl.microsoft.com/download/symbols`.
4. Converts PDBs to LibVMI JSON profiles using `rekall` or `drakvuf-sandbox` profile tools.

---

## 3. Detailed Phase Breakdown

### Phase 0: Pre-Flight Qualification & Diagnostics
- **Target:** Verify host viability before writing any files.
- **Actions:**
  1. Check root permissions (`UID == 0`).
  2. Inspect CPU architecture (`x86_64`) and vendor (`GenuineIntel`).
  3. Validate flags: `vmx`, `ept`, `flexpriority`, `vpid`.
  4. Ensure system is NOT running in an unsupported nested cloud hypervisor (AWS EC2, Google Cloud, Azure) where EPT virtualization is suppressed.
  5. Check free disk space (minimum 60 GB required for Xen, DRAKVUF, ISO, and VM disk images).
  6. Verify bootloader is standard GRUB2 (`/boot/grub/grub.cfg` exists).

### Phase 1: Xen Hypervisor Deployment & GRUB Configuration
- **Target:** Install Xen 4.19 and configure the Linux kernel to run under Dom0.
- **Actions:**
  1. Install system toolchains: `gcc`, `clang`, `bison`, `flex`, `meson`, `ninja-build`, `libaio-dev`, `libglib2.0-dev`, `libpixman-1-dev`, `iasl`, `bridge-utils`, `iproute2`.
  2. Fetch Xen sources (Xen 4.19.2) or evaluate optimized prebuilt packages from `tklengyel/drakvuf-builds`.
  3. Apply known stability patches (OVMF Tianocore Git submodule fix: `edk2-stable202408.01`).
  4. Compile Xen hypervisor and tools:
     ```bash
     ./configure --enable-githttp --enable-systemd --enable-ovmf --disable-pvshim
     make -j$(nproc) dist-xen
     make -j$(nproc) dist-tools
     make -j$(nproc) debball
     ```
  5. Configure Xen bootloader line in `/etc/default/grub`:
     ```bash
     GRUB_CMDLINE_XEN_DEFAULT="dom0_mem=4096M,max:4096M dom0_max_vcpus=2 dom0_vcpus_pin=1 force-ept=1 ept=ad=0 hap_1gb=0 hap_2mb=0 altp2m=1 hpet=legacy-replacement smt=0 spec-ctrl=gds-mit=no"
     ```
  6. Enable Xen runtime kernel modules in `/etc/modules`: `xen-evtchn`, `xen-privcmd`, `xen-gntdev`.
  7. Enable Xen management services: `xencommons`, `xen-qemu-dom0-disk-backend`, `xen-init-dom0`, `xenconsoled`.
  8. Run `update-grub` and set Xen as default entry in GRUB.
  9. Install auto-resume one-shot unit `/etc/systemd/system/drakvuf-installer-resume.service`.
  10. Update state: `mark_phase_complete("phase_1_xen_installed")`. Prompt or execute system reboot.

### Phase 2: Post-Reboot Verification & Handshake
- **Target:** Verify that the system successfully booted into Xen Dom0.
- **Actions:**
  1. Triggered automatically on boot via `drakvuf-installer-resume.service` (or manually via `drakvuf-auto install --resume`).
  2. Execute `xen-detect` — must return: `Running in PV context on Xen V4.x`.
  3. Execute `xl list` — must verify `Domain-0` is running with 4096M assigned memory.
  4. Verify `/proc/xen/privcmd` is mounted and accessible.
  5. Remove `/etc/systemd/system/drakvuf-installer-resume.service` to prevent boot loops.
  6. Update state: `mark_phase_complete("phase_2_xen_active")`.

### Phase 3: LibVMI & DRAKVUF Engine Compilation
- **Target:** Build and install the core introspection binaries.
- **Actions:**
  1. Clone `https://github.com/tklengyel/drakvuf.git` recursively with submodules.
  2. Build `libvmi`:
     ```bash
     cd /opt/drakvuf/libvmi
     autoreconf -vif
     ./configure --disable-kvm --disable-bareflank --disable-file
     make -j$(nproc) && make install
     ldconfig
     ```
  3. Validate LibVMI binaries: `vmi-win-guid`, `vmi-win-offsets`, `vmi-process-list`.
  4. Build DRAKVUF Engine:
     ```bash
     cd /opt/drakvuf
     meson setup build --native-file llvm.ini
     ninja -C build
     install -m 755 build/drakvuf build/injector /usr/local/bin/
     ```
  5. Validate engine binaries: run `drakvuf --version` and `injector --help`.
  6. Update state: `mark_phase_complete("phase_3_drakvuf_engine_installed")`.

### Phase 4: Network Bridge & Virtualization Storage Subsystem
- **Target:** Create Xen networking and storage for guest virtual machines.
- **Actions:**
  1. Create Xen bridge interface `xenbr0` via `systemd-networkd` or `bridge-utils`.
  2. Configure NAT routing and IP forwarding (`net.ipv4.ip_forward = 1`) via `nftables` or `iptables`.
  3. Set up isolated DNS/DHCP server (`dnsmasq`) for subnet `192.168.100.0/24`.
  4. Allocate sparse or raw disk image (`/var/lib/drakvuf/images/win10.img`, 40GB).
  5. Update state: `mark_phase_complete("phase_4_network_storage_ready")`.

### Phase 5: Windows 10/11 HVM Automated Installation
- **Target:** Create a clean, vanilla Windows guest virtual machine without in-guest agents.
- **Actions:**
  1. Download or verify Windows 10 ISO (22H2 x64 recommended).
  2. Inject `autounattend.xml` with zero-touch configuration:
     - Automated partitioning (`Disk 0`).
     - Automated administrator account creation (`drakvuf` / `Password123!`).
     - OOBE network screen bypass (`BypassNRO`).
     - Windows Defender disabled via registry policy (to prevent interference during malware analysis).
     - Windows Update, Sleep, and Telemetry permanently disabled.
  3. Generate Xen domain configuration file (`/etc/xen/win10.cfg`):
     ```
     type = "hvm"
     name = "win10-drakvuf"
     memory = 4096
     vcpus = 2
     disk = [ '/var/lib/drakvuf/images/win10.img,raw,xvda,w' ]
     vif = [ 'bridge=xenbr0' ]
     boot = "dc"
     vnc = 1
     vnclisten = "127.0.0.1"
     ```
  4. Boot VM with `xl create /etc/xen/win10.cfg`.
  5. Monitor installation lifecycle until guest OS reaches complete idle state.
  6. Update state: `mark_phase_complete("phase_5_windows_guest_installed")`.

### Phase 6: Kernel Symbol Extraction & LibVMI JSON Profile Synthesis
- **Target:** Provide DRAKVUF with the exact memory offsets for the guest Windows build.
- **Actions:**
  1. Mount guest Windows disk using `kpartx` / `qemu-nbd` or query live domain via `vmi-win-guid win10-drakvuf`.
  2. Extract `ntoskrnl.exe`, `ntdll.dll`, `win32k.sys`, and `kernel32.dll`.
  3. Parse PE headers to extract the CodeView PDB debug signature (GUID + Age).
  4. Download official `.pdb` files from Microsoft Public Symbol Server:
     `https://msdl.microsoft.com/download/symbols/<pdb_name>/<guid><age>/<pdb_name>`
  5. Execute profile generator tool (`draksetup` / `rekall` / `pdbex`) to compute structure offsets (`_EPROCESS.ActiveProcessLinks`, `_KTHREAD`, `_PEB`, System Call Table).
  6. Save compiled JSON profile to `/etc/libvmi/win10.json`.
  7. Validate profile by running:
     ```bash
     vmi-process-list -n win10-drakvuf
     ```
     *(Must output clean list of running Windows processes directly from hypervisor memory).*
  8. Update state: `mark_phase_complete("phase_6_symbols_generated")`.

### Phase 7: DRAKVUF Sandbox Microservices Stack
- **Target:** Deploy CERT Polska’s orchestration backend, task queues, and Web UI.
- **Actions:**
  1. Install Redis for internal task queueing.
  2. Install MinIO (or configure local S3-compatible backend) for analysis artifact and memory dump storage.
  3. Install `drakcore` and `draksystem` worker dispatchers.
  4. Install `drakweb` Web UI (Flask / React interface).
  5. Configure systemd unit files:
     - `drakcore.service`
     - `drakweb.service`
     - `draksystem.service`
  6. Enable and start all services via `systemctl enable --now`.
  7. Update state: `mark_phase_complete("phase_7_services_active")`.

### Phase 8: Verification, Test Submission, & Diagnostics
- **Target:** Validate that malware execution is actively introspected and reported.
- **Actions:**
  1. Submit a test sample (`pafish.exe` or benign execution probe) to `drakweb` API.
  2. Monitor `drakvuf` hypervisor worker logs in real time.
  3. Verify EPT/Altp2m traps are firing for process creation (`NtCreateProcess`, `NtWriteVirtualMemory`).
  4. Check that behavioral JSON reports and PCAP network logs are saved to MinIO/storage.
  5. Validate HTTP 200 on Web UI (`http://127.0.0.1:6300` or configured port).
  6. Output installation summary, credentials, and access endpoints in Rich terminal banner.
  7. Update state: `mark_phase_complete("phase_8_verified")`.

---

## 4. Codebase Architecture

The project will be organized cleanly in `drakvuf-auto-installer`:

```
drakvuf-auto-installer/
├── config.toml                   # Central user configuration file
├── PLAN.md                       # Master architectural blueprint
├── README.md                     # Documentation & user guide
├── install.sh                    # Unified shell wrapper entrypoint
├── clean-install.sh              # Reset state and reinstall from scratch
├── diagnose.sh                   # Comprehensive environment and service diagnostic tool
├── status.sh                     # Live status of hypervisor, VM, and sandbox services
├── repair.sh                     # Automated healing for common Xen/VMI issues
├── uninstall.sh                  # Safe teardown and cleanup
│
├── src/
│   └── drakvuf_auto/
│       ├── __init__.py           # Package version and metadata
│       ├── cli.py                # Typer CLI application (install, resume, diagnose, test)
│       ├── config.py             # Pydantic v2 strict configuration models
│       ├── state.py              # Atomic JSON state engine with checkpoint rollback
│       ├── command.py            # Live process execution runner with streaming logs
│       ├── logging_setup.py      # Rich console & rotating file logging setup
│       ├── orchestrator.py       # Master multi-phase lifecycle orchestrator
│       ├── diagnostics.py        # CPU, Xen, LibVMI, and service health checks
│       ├── remediation.py        # Automated issue resolvers (subhook, GRUB, symbols)
│       │
│       ├── phases/               # Modular Phase Handlers
│       │   ├── phase0_preflight.py
│       │   ├── phase1_xen.py
│       │   ├── phase2_resume.py
│       │   ├── phase3_engine.py
│       │   ├── phase4_network.py
│       │   ├── phase5_guest.py
│       │   ├── phase6_symbols.py
│       │   ├── phase7_services.py
│       │   └── phase8_verify.py
│       │
│       └── vmi/                  # VMI & Profiling Utilities
│           ├── pdb_fetcher.py    # Microsoft Symbol Server client
│           └── profile_maker.py  # JSON profile builder from extracted binaries
│
├── templates/
│   ├── grub/                     # GRUB Xen command line configuration
│   ├── systemd/                  # Resume unit, drakcore, drakweb, draksystem services
│   ├── xen/                      # win10.cfg HVM domain templates
│   ├── windows/                  # autounattend.xml zero-touch answer files
│   └── patches/                  # Xen and OVMF compilation hotfixes
│
├── scripts/                      # Standalone helper scripts
├── state/                        # State persistence (state.json)
├── logs/                         # Detailed installation and runtime logs
├── reports/                      # Diagnostic and verification reports
└── backups/                      # Backup copies of configuration files
```

---

## 5. Potential Hazards, Edge Cases & Automated Remediation

| Hazard / Failure Mode | Root Cause | Automated Remediation in `drakvuf-auto` |
| :--- | :--- | :--- |
| **Unsupported CPU** | AMD processor or Intel CPU without EPT. | Phase 0 detects immediately, prints clear hardware diagnostics, and aborts before altering any system files. |
| **Xen OVMF Build Failure** | Tianocore broken submodule Git credentials bug. | Automatically applies `templates/patches/ovmf_subhook.patch` replacing commit hash with `edk2-stable202408.01`. |
| **GDS / AVX Instruction Crash** | Xen enables Downfall GDS mitigation by disabling AVX in guest. | Appends `spec-ctrl=gds-mit=no` to `GRUB_CMDLINE_XEN_DEFAULT`. |
| **Host Fails to Boot into Xen** | GRUB default menu index not updated or UEFI NVRAM issue. | Configures `GRUB_DEFAULT="Xen 4.19"` explicitly via `grub-set-default` and validates `grub.cfg` syntax before reboot. |
| **Symbol Fetch Timeout** | Microsoft Symbol Server throttles or drops connection. | Retries with exponential backoff; caches downloaded PDBs locally in `cache/symbols/`. |
| **VMI Profile Mismatch** | Windows Update pushed a kernel patch changing `_EPROCESS` offsets. | Freezes Windows Updates via unattended registry keys; auto-regenerates profile if kernel hash changes. |
| **State Interruption** | Power failure, SSH disconnect, or manual cancellation. | State engine saves progress at every step; running `install.sh` resumes exactly where it stopped. |

---

## 6. Implementation Milestones

- **Milestone 1 (Foundation):** Base repository structure, configuration schema (`config.toml`), atomic state engine (`state.py`), and pre-flight diagnostics module (`phase0_preflight.py`).
- **Milestone 2 (Xen Hypervisor & Reboot Engine):** Xen 4.19 build scripts, GRUB configuration generator, and systemd auto-resume unit (`phase1_xen.py` & `phase2_resume.py`).
- **Milestone 3 (DRAKVUF & LibVMI Core):** LibVMI and DRAKVUF engine compilation pipeline, self-test verification (`phase3_engine.py`).
- **Milestone 4 (Virtualization Infrastructure):** Xen network bridge, DHCP daemon, and disk image provisioning (`phase4_network.py`).
- **Milestone 5 (Windows Guest & Symbols):** Unattended Windows 10 deployment, PDB downloader, and LibVMI JSON profile synthesis (`phase5_guest.py` & `phase6_symbols.py`).
- **Milestone 6 (Web UI & Services):** Integration of `drakcore`, `drakweb`, Redis, and MinIO systemd units (`phase7_services.py`).
- **Milestone 7 (Validation & Release):** Automated analysis verification with `pafish.exe`, diagnostic tooling (`diagnose.sh`, `repair.sh`), and production documentation.

---
*Developed by Nitiraj Kulkarni for high-fidelity, agentless malware analysis infrastructure.*
