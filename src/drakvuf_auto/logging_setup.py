"""Logging infrastructure for DRAKVUF Sandbox Auto-Installer.

Author: Nitiraj Kulkarni
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None  # type: ignore
    RichHandler = None  # type: ignore
    Panel = None  # type: ignore
    Text = None  # type: ignore

console = Console() if RICH_AVAILABLE else None


def setup_logging(
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    console_output: bool = True
) -> logging.Logger:
    """Configure structured logging with console and file handlers."""
    logger = logging.getLogger("drakvuf_auto")
    logger.setLevel(level)
    logger.handlers.clear()

    if console_output:
        if RICH_AVAILABLE and console:
            rich_handler = RichHandler(
                console=console,
                show_time=True,
                show_path=False,
                markup=True,
                rich_tracebacks=True,
            )
            rich_handler.setLevel(level)
            logger.addHandler(rich_handler)
        else:
            std_handler = logging.StreamHandler(sys.stdout)
            std_handler.setLevel(level)
            std_formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            std_handler.setFormatter(std_formatter)
            logger.addHandler(std_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def print_banner(title: str, subtitle: str = "") -> None:
    """Print an attractive header banner in the terminal."""
    if RICH_AVAILABLE and console:
        content = f"[bold cyan]{title}[/bold cyan]"
        if subtitle:
            content += f"\n[dim white]{subtitle}[/dim white]"
        console.print(Panel(content, border_style="bold blue", expand=False))
    else:
        print("=" * 70)
        print(f"  {title}")
        if subtitle:
            print(f"  {subtitle}")
        print("=" * 70)
