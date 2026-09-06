"""
Roles — named bundles of (a) which Action and (b) its color/identity for the UI.

A Role can be re-invoked (e.g. Engineer re-runs after QA fail) — we track
attempts so the UI can show "round 2".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

from .actions import WriteCode, WriteDesign, WritePRD, WriteTest
from .llm import LLM
from .schema import Message, MessagePool


@dataclass
class Role:
    name: str
    profile: str
    color: str           # for the UI (red/green/blue/etc.)
    actions: List[Callable] = field(default_factory=list)
    action_names: List[str] = field(default_factory=list)

    def run(self, pool: MessagePool, *, on_token=None, round_num: int = 0,
            qa_feedback=None) -> List[Message]:
        outs = []
        for action_factory, action_name in zip(self.actions, self.action_names):
            action = action_factory()
            if action_name == "WriteCode":
                # Engineer returns (Message, Manifest) — unpack
                msg, _ = action.run(pool, on_token=on_token,
                                    round_num=round_num, qa_feedback=qa_feedback)
            else:
                msg = action.run(pool, on_token=on_token, round_num=round_num)
            outs.append(msg)
        return outs


def make_canonical_team(llm: LLM) -> List[Role]:
    """PM → Architect → Engineer → QA. The MetaGPT canonical SOP."""
    return [
        Role("ProductManager", "Senior PM", color="cyan",
             actions=[lambda: WritePRD(llm)],
             action_names=["WritePRD"]),
        Role("Architect", "Senior Architect", color="magenta",
             actions=[lambda: WriteDesign(llm)],
             action_names=["WriteDesign"]),
        Role("Engineer", "Senior Backend Engineer", color="green",
             actions=[lambda: WriteCode(llm)],
             action_names=["WriteCode"]),
        Role("QA", "Senior QA Engineer", color="yellow",
             actions=[lambda: WriteTest(llm)],
             action_names=["WriteTest"]),
    ]