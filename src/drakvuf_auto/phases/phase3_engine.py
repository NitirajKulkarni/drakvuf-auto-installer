"""Phase 3: LibVMI & DRAKVUF Engine Compilation.

Author: Nitiraj Kulkarni
"""

import logging
from pathlib import Path

from drakvuf_auto.command import command_exists, run_command
from drakvuf_auto.config import DrakvufAutoConfig
from drakvuf_auto.exceptions import EngineCompilationError
from drakvuf_auto.state import StateManager

logger = logging.getLogger("drakvuf_auto.phase3")


def execute_phase_3(config: DrakvufAutoConfig, state: StateManager, project_root: Path) -> None:
    """Clone, compile, and install LibVMI and the DRAKVUF introspection engine."""
    phase_name = "phase_3_engine_build"
    if state.is_phase_completed(phase_name):
        logger.info("[bold green]Phase 3 (DRAKVUF Engine) already completed. Skipping.[/bold green]")
        return

    state.start_phase(phase_name)
    logger.info("Starting Phase 3: LibVMI & DRAKVUF Engine Compilation...")

    drakvuf_dir = config.installation.drakvuf_root

    # Step 1: Clone DRAKVUF source tree with submodules
    step_clone = "clone_drakvuf_repo"
    if not state.is_step_completed(phase_name, step_clone):
        state.start_step(phase_name, step_clone)
        logger.info(f"Cloning DRAKVUF repository into {drakvuf_dir}...")
        drakvuf_dir.parent.mkdir(parents=True, exist_ok=True)
        if not (drakvuf_dir / ".git").exists():
            run_command(
                ["git", "clone", "--recursive", config.drakvuf.repo, str(drakvuf_dir)],
                stream=True
            )
        else:
            run_command(["git", "submodule", "update", "--init", "--recursive"], cwd=drakvuf_dir, stream=True)
        state.complete_step(phase_name, step_clone)

    # Step 2: Build LibVMI with Xen introspection support
    step_libvmi = "build_libvmi"
    if not state.is_step_completed(phase_name, step_libvmi):
        state.start_step(phase_name, step_libvmi)
        logger.info("Building LibVMI...")
        libvmi_dir = drakvuf_dir / "libvmi"
        if not libvmi_dir.exists():
            raise EngineCompilationError(f"LibVMI directory not found at {libvmi_dir}")

        run_command(["autoreconf", "-vif"], cwd=libvmi_dir, stream=True)
        run_command(
            ["./configure", "--disable-kvm", "--disable-bareflank", "--disable-file"],
            cwd=libvmi_dir,
            stream=True
        )
        run_command(["make", f"-j{min(4, os_cpu_count())}"], cwd=libvmi_dir, stream=True)
        run_command(["make", "install"], cwd=libvmi_dir, stream=True)

        # Update dynamic linker cache
        ld_conf = Path("/etc/ld.so.conf.d/drakvuf.conf")
        ld_conf.write_text("/usr/local/lib\n", encoding="utf-8")
        run_command(["ldconfig"], stream=False)

        # Test vmi-win-guid
        if not command_exists("vmi-win-guid"):
            raise EngineCompilationError("vmi-win-guid executable not found after LibVMI build")
        state.complete_step(phase_name, step_libvmi)

    # Step 3: Build DRAKVUF Engine & Injector
    step_engine = "build_drakvuf_engine"
    if not state.is_step_completed(phase_name, step_engine):
        state.start_step(phase_name, step_engine)
        logger.info("Compiling DRAKVUF engine and injector via Meson/Ninja...")

        build_dir = drakvuf_dir / "build"
        if not build_dir.exists():
            run_command(["meson", "setup", "build", "--native-file", "llvm.ini"], cwd=drakvuf_dir, stream=True)

        run_command(["ninja", "-C", "build"], cwd=drakvuf_dir, stream=True)

        # Install binaries to /usr/local/bin
        drakvuf_bin = build_dir / "drakvuf"
        injector_bin = build_dir / "injector"
        if drakvuf_bin.exists():
            run_command(["install", "-m", "755", str(drakvuf_bin), "/usr/local/bin/drakvuf"], stream=False)
        if injector_bin.exists():
            run_command(["install", "-m", "755", str(injector_bin), "/usr/local/bin/injector"], stream=False)

        # Verify binaries
        if not command_exists("drakvuf") or not command_exists("injector"):
            raise EngineCompilationError("drakvuf or injector binary missing from /usr/local/bin")

        state.complete_step(phase_name, step_engine)

    state.complete_phase(phase_name)
    logger.info("[bold green]✓ Phase 3 completed: DRAKVUF engine and LibVMI built and installed.[/bold green]")


def os_cpu_count() -> int:
    import os
    return os.cpu_count() or 2
