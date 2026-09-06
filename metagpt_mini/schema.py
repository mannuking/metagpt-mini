"""
Core SOP substrate — `Message`, `Role`, and the shared `MessagePool`.

This is the data model that every agent in MetaGPT reasons over. The pool is
the *shared environment*: every agent reads from it and writes into it.

Per the MetaGPT paper §3 (Message), each message has:
- role: who emitted it (PM, Architect, Engineer, QA)
- content: the actual text
- cause_by: which Action produced it (WritePRD, WriteDesign, …)

This is what makes the SOP traceable. It's also the cheapest possible
implementation of an event-driven agent runtime.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass
class Message:
    role: str                       # emitting role name, e.g. "ProductManager"
    content: str                    # free-form text (PRD, design doc, code, etc.)
    cause_by: str = ""              # producing Action, e.g. "WritePRD"
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __repr__(self) -> str:
        return f"[{self.role} → {self.cause_by}] {self.content[:120]}{'…' if len(self.content) > 120 else ''}"


class MessagePool:
    """Shared bus — every agent in the team reads from and writes into the same pool."""

    def __init__(self):
        self.messages: List[Message] = []

    def publish(self, msg: Message) -> None:
        self.messages.append(msg)

    def history(self) -> List[Message]:
        """All messages, in order."""
        return list(self.messages)

    def of_role(self, role_name: str) -> List[Message]:
        """Messages produced by a specific role."""
        return [m for m in self.messages if m.role == role_name]

    def by_action(self, cause_by: str) -> List[Message]:
        """Messages produced by a specific Action."""
        return [m for m in self.messages if m.cause_by == cause_by]