"""Command execution subsystem with real-time streaming and logging.

Author: Nitiraj Kulkarni
"""

import logging
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

logger = logging.getLogger("drakvuf_auto.command")


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float

    @property
    def success(self) -> bool:
        return self.returncode == 0


def run_command(
    cmd: Union[str, List[str]],
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
    stream: bool = True,
    check: bool = True,
    shell: bool = False,
) -> CommandResult:
    """Execute a system command with real-time log streaming and capture."""
    if isinstance(cmd, list) and not shell:
        cmd_str = " ".join(shlex.quote(str(c)) for c in cmd)
        args = [str(c) for c in cmd]
    elif isinstance(cmd, str):
        cmd_str = cmd
        args = cmd if shell else shlex.split(cmd)
    else:
        cmd_str = " ".join(str(c) for c in cmd)
        args = cmd_str

    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    logger.debug(f"Executing: {cmd_str} (cwd={cwd})")
    start_time = time.time()

    process = subprocess.Popen(
        args,
        cwd=str(cwd) if cwd else None,
        env=merged_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        shell=shell,
        universal_newlines=True,
    )

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []

    try:
        # Stream stdout in real-time
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                stdout_lines.append(line)
                if stream:
                    line_clean = line.rstrip()
                    if line_clean:
                        logger.info(line_clean)
            process.stdout.close()

        # Capture stderr
        if process.stderr:
            for line in iter(process.stderr.readline, ""):
                stderr_lines.append(line)
                if stream:
                    line_clean = line.rstrip()
                    if line_clean:
                        logger.warning(line_clean)
            process.stderr.close()

        returncode = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        logger.error(f"Command timed out after {timeout}s: {cmd_str}")
        raise
    except Exception as e:
        process.kill()
        logger.error(f"Command execution error: {e}")
        raise

    duration = time.time() - start_time
    stdout_text = "".join(stdout_lines)
    stderr_text = "".join(stderr_lines)

    result = CommandResult(
        command=cmd_str,
        returncode=returncode,
        stdout=stdout_text,
        stderr=stderr_text,
        duration_seconds=duration,
    )

    if check and returncode != 0:
        err_msg = (
            f"Command failed with exit code {returncode}: {cmd_str}\n"
            f"Stderr: {stderr_text.strip() or stdout_text.strip()}"
        )
        logger.error(err_msg)
        raise subprocess.CalledProcessError(
            returncode=returncode,
            cmd=cmd_str,
            output=stdout_text,
            stderr=stderr_text,
        )

    return result


def command_exists(binary_name: str) -> bool:
    """Check if an executable is present in PATH."""
    return shutil_which(binary_name) is not None


def shutil_which(binary_name: str) -> Optional[str]:
    import shutil
    return shutil.which(binary_name)
