"""
Roles — the agents. A Role is a named bundle of (a) Action classes and (b) a
run method that executes them against the shared MessagePool.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .actions import WriteCode, WriteDesign, WritePRD, WriteTest
from .llm import LLM
from .schema import Message, MessagePool


@dataclass
class Role:
    name: str
    profile: str  # human-readable role profile
    actions: List[Callable] = field(default_factory=list)
    action_names: List[str] = field(default_factory=list)

    def run(self, pool: MessagePool, *, on_token=None) -> List[Message]:
        outs = []
        for action_factory, action_name in zip(self.actions, self.action_names):
            action = action_factory()
            # Pass action_name via on_token context — UI needs to display it
            msg = action.run(pool, on_token=on_token) if hasattr(action, "run") else action(pool)
            outs.append(msg)
        return outs


# ── Canonical team ─────────────────────────────────────────────────────────

def make_canonical_team(llm: LLM) -> List[Role]:
    """PM → Architect → Engineer → QA. The MetaGPT canonical SOP."""
    return [
        Role("ProductManager", "Senior PM",
             actions=[lambda: WritePRD(llm)],
             action_names=["WritePRD"]),
        Role("Architect", "Senior Architect",
             actions=[lambda: WriteDesign(llm)],
             action_names=["WriteDesign"]),
        Role("Engineer", "Senior Backend Engineer",
             actions=[lambda: WriteCode(llm)],
             action_names=["WriteCode"]),
        Role("QA", "Senior QA Engineer",
             actions=[lambda: WriteTest(llm)],
             action_names=["WriteTest"]),
    ]