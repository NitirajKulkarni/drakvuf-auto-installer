"""Atomic State Engine with reboot tracking and checkpoint recovery.

Author: Nitiraj Kulkarni
"""

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Status(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepRecord(BaseModel):
    name: str
    status: Status = Status.PENDING
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    error: Optional[str] = None
    retries: int = 0
    data: Dict[str, Any] = Field(default_factory=dict)


class PhaseRecord(BaseModel):
    name: str
    status: Status = Status.PENDING
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    error: Optional[str] = None
    steps: Dict[str, StepRecord] = Field(default_factory=dict)


class InstallerState(BaseModel):
    version: str = "1.0.0"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    active_phase: Optional[str] = None
    reboot_pending: bool = False
    reboot_completed: bool = False
    phases: Dict[str, PhaseRecord] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StateManager:
    """Manages atomic reads/writes to the state file."""

    def __init__(self, state_file: Path):
        self.state_file = Path(state_file)
        self.state = self._load()

    def _load(self) -> InstallerState:
        if not self.state_file.exists():
            state = InstallerState()
            self._save(state)
            return state

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return InstallerState.model_validate(data)
        except Exception:
            # Backup corrupted state file if it exists
            backup = self.state_file.with_suffix(".json.corrupted")
            shutil.copy2(self.state_file, backup)
            state = InstallerState()
            self._save(state)
            return state

    def _save(self, state: Optional[InstallerState] = None) -> None:
        """Atomic write using temporary file to prevent corruption."""
        if state is not None:
            self.state = state

        self.state.updated_at = datetime.now(timezone.utc).isoformat()
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        temp_fd, temp_path = tempfile.mkstemp(
            dir=str(self.state_file.parent),
            prefix="state_",
            suffix=".tmp"
        )
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(self.state.model_dump(), f, indent=2)
            shutil.move(temp_path, str(self.state_file))
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def start_phase(self, phase_name: str) -> None:
        if phase_name not in self.state.phases:
            self.state.phases[phase_name] = PhaseRecord(name=phase_name)
        phase = self.state.phases[phase_name]
        phase.status = Status.IN_PROGRESS
        phase.start_time = datetime.now(timezone.utc).isoformat()
        phase.error = None
        self.state.active_phase = phase_name
        self._save()

    def complete_phase(self, phase_name: str) -> None:
        if phase_name in self.state.phases:
            phase = self.state.phases[phase_name]
            phase.status = Status.COMPLETED
            phase.end_time = datetime.now(timezone.utc).isoformat()
            phase.error = None
        if self.state.active_phase == phase_name:
            self.state.active_phase = None
        self._save()

    def fail_phase(self, phase_name: str, error: str) -> None:
        if phase_name in self.state.phases:
            phase = self.state.phases[phase_name]
            phase.status = Status.FAILED
            phase.end_time = datetime.now(timezone.utc).isoformat()
            phase.error = error
        self._save()

    def is_phase_completed(self, phase_name: str) -> bool:
        phase = self.state.phases.get(phase_name)
        return phase is not None and phase.status == Status.COMPLETED

    def start_step(self, phase_name: str, step_name: str) -> None:
        if phase_name not in self.state.phases:
            self.start_phase(phase_name)
        phase = self.state.phases[phase_name]
        if step_name not in phase.steps:
            phase.steps[step_name] = StepRecord(name=step_name)
        step = phase.steps[step_name]
        step.status = Status.IN_PROGRESS
        step.start_time = datetime.now(timezone.utc).isoformat()
        step.error = None
        self._save()

    def complete_step(self, phase_name: str, step_name: str, data: Optional[Dict[str, Any]] = None) -> None:
        if phase_name in self.state.phases:
            phase = self.state.phases[phase_name]
            if step_name in phase.steps:
                step = phase.steps[step_name]
                step.status = Status.COMPLETED
                step.end_time = datetime.now(timezone.utc).isoformat()
                step.error = None
                if data:
                    step.data.update(data)
        self._save()

    def fail_step(self, phase_name: str, step_name: str, error: str) -> None:
        if phase_name in self.state.phases:
            phase = self.state.phases[phase_name]
            if step_name in phase.steps:
                step = phase.steps[step_name]
                step.status = Status.FAILED
                step.end_time = datetime.now(timezone.utc).isoformat()
                step.error = error
                step.retries += 1
        self._save()

    def is_step_completed(self, phase_name: str, step_name: str) -> bool:
        phase = self.state.phases.get(phase_name)
        if not phase:
            return False
        step = phase.steps.get(step_name)
        return step is not None and step.status == Status.COMPLETED

    def set_reboot_pending(self, pending: bool = True) -> None:
        self.state.reboot_pending = pending
        self._save()

    def set_reboot_completed(self, completed: bool = True) -> None:
        self.state.reboot_completed = completed
        self.state.reboot_pending = False
        self._save()

    def reset(self) -> None:
        """Clear state and reset to clean starting state."""
        self.state = InstallerState()
        self._save()
