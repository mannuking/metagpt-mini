"""
Core SOP substrate — Message, MessagePool, Manifest, run_id.

The Message is the atomic unit every agent exchanges. The Manifest is the
structured output from the Engineer (multi-file project structure).
run_id ties everything in a single run together.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class Message:
    role: str                       # emitting role name, e.g. "ProductManager"
    content: str                    # free-form text (PRD, design doc, code, etc.)
    cause_by: str = ""              # producing Action, e.g. "WritePRD"
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    round_num: int = 0              # which Engineer->QA iteration this is in
    extra: dict = field(default_factory=dict)  # file paths, manifest refs, etc.

    def __repr__(self) -> str:
        return f"[{self.role} → {self.cause_by} round={self.round_num}] {self.content[:120]}{'…' if len(self.content) > 120 else ''}"


class MessagePool:
    """Shared bus — every agent in the team reads from and writes into the same pool."""

    def __init__(self):
        self.messages: List[Message] = []

    def publish(self, msg: Message) -> None:
        self.messages.append(msg)

    def history(self) -> List[Message]:
        return list(self.messages)

    def of_role(self, role_name: str) -> List[Message]:
        return [m for m in self.messages if m.role == role_name]

    def by_action(self, cause_by: str) -> List[Message]:
        return [m for m in self.messages if m.cause_by == cause_by]

    def latest_of(self, cause_by: str) -> Optional[Message]:
        matches = self.by_action(cause_by)
        return matches[-1] if matches else None


# ── Run ID ─────────────────────────────────────────────────────────────────
def new_run_id(requirement: str) -> str:
    """Short, deterministic-per-requirement run id like 'a3f7c-2026-09-06'."""
    h = hashlib.sha1(requirement.encode()).hexdigest()[:5]
    return f"{h}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"


# ── Manifest (Engineer output) ─────────────────────────────────────────────
@dataclass
class FileEntry:
    path: str
    content: str
    rationale: str = ""


@dataclass
class Manifest:
    """The Engineer's structured output: a set of files to write to disk."""
    project_name: str
    summary: str
    files: List[FileEntry] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # pip packages
    run_instructions: str = ""   # how to run the generated project

    def total_chars(self) -> int:
        return sum(len(f.content) for f in self.files)

    def file_paths(self) -> List[str]:
        return [f.path for f in self.files]