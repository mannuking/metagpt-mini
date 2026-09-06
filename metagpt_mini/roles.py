"""
Roles — the agents. A Role is a named bundle of (a) Action classes and (b) a
run method that executes them against the shared MessagePool.

In MetaGPT a Role is more dynamic (multi-actor, watching for specific message
types). For pedagogical clarity we keep the static one-action-per-role model —
the four canonical software-team roles from §4 of the paper.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Type

from .actions import WriteCode, WriteDesign, WritePRD, WriteTest
from .llm import LLM
from .schema import Message, MessagePool


@dataclass
class Role:
    name: str
    profile: str  # human-readable role profile
    actions: List[Callable] = field(default_factory=list)

    def run(self, pool: MessagePool) -> List[Message]:
        outs = []
        for action_factory in self.actions:
            # Action factories are the @dataclass classes above; instantiate + run.
            action = action_factory()
            # `action` is a dataclass instance with `.run(pool)` -> Message
            msg = action.run(pool) if hasattr(action, "run") else action(pool)
            outs.append(msg)
        return outs


# ── Canonical team ─────────────────────────────────────────────────────────

def make_canonical_team(llm: LLM) -> List[Role]:
    """PM → Architect → Engineer → QA. The MetaGPT canonical SOP."""
    return [
        Role("ProductManager", "Senior PM", actions=[lambda: WritePRD(llm)]),
        Role("Architect",      "Senior Architect", actions=[lambda: WriteDesign(llm)]),
        Role("Engineer",       "Senior Backend Engineer", actions=[lambda: WriteCode(llm)]),
        Role("QA",             "Senior QA Engineer", actions=[lambda: WriteTest(llm)]),
    ]