"""
Actions — the verbs in the SOP.

Each Action is a pure async-style function that takes a context (pool + upstream
messages) and emits a single Message. This is exactly MetaGPT's Action abstraction:

> Action is a fundamental unit that defines how to transform input into output.
> (Hong et al., 2024, §3.2)

We expose four canonical actions, in SOP order:
1. WritePRD     — ProductManager
2. WriteDesign  — Architect
3. WriteCode    — Engineer
4. WriteTest    — QA
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from .llm import LLM, ChatMessage
from .schema import Message, MessagePool


# ── Helpers ────────────────────────────────────────────────────────────────

def _last_of(pool: MessagePool, cause_by: str) -> Message | None:
    matches = pool.by_action(cause_by)
    return matches[-1] if matches else None


def _format_pool(pool: MessagePool) -> str:
    """Serialize the pool as text the LLM can consume."""
    lines = []
    for m in pool.history():
        lines.append(f"### From {m.role} ({m.cause_by})\n{m.content}\n")
    return "\n".join(lines) or "(no prior messages)"


def _user_requirement(pool: MessagePool) -> str:
    seed = next((m for m in pool.history() if m.role == "User"), None)
    return seed.content if seed else "(no requirement provided)"


# ── Actions ─────────────────────────────────────────────────────────────────

PRD_SYSTEM = (
    "You are a senior Product Manager. Given a user requirement, produce a "
    "concise PRD with these sections:\n"
    "1. Goal (one paragraph)\n"
    "2. User Stories (3-5 bullets, 'As a X, I want Y, so Z')\n"
    "3. Functional Requirements (numbered list)\n"
    "4. Non-Functional Requirements (latency, cost, security)\n"
    "5. Out-of-scope (one paragraph)\n"
    "Be specific and grounded. No filler."
)

DESIGN_SYSTEM = (
    "You are a senior Software Architect. Convert the PRD into a technical design with:\n"
    "1. Architecture overview\n3. Module breakdown (file paths + responsibilities)\n"
    "4. Data model (classes / dataclasses)\n"
    "5. Interface contracts (function signatures + types)\n"
    "6. Edge cases\n"
    "Output code-ready design — no marketing language."
)

CODE_SYSTEM = (
    "You are a senior Backend Engineer. Implement the design in production-quality "
    "Python. Use only the standard library unless the design specifies otherwise. "
    "Output the COMPLETE file contents in a single fenced ```python block. "
    "Include a docstring at the top, type hints, and a `if __name__ == \"__main__\"` "
    "demo. No TODOs."
)

TEST_SYSTEM = (
    "You are a senior QA Engineer. Write a pytest test module that exercises the "
    "happy path, edge cases, and at least one failure case for the code below. "
    "Output the COMPLETE test file in a fenced ```python block."
)


@dataclass
class WritePRD:
    llm: LLM
    cause_by: str = "WritePRD"
    role_name: str = "ProductManager"

    def run(self, pool: MessagePool, *, on_token=None) -> Message:
        requirement = _user_requirement(pool)
        # on_token: callable(str) -> None, called for each token chunk
        sys_msg = ChatMessage("system", PRD_SYSTEM)
        user_msg = ChatMessage("user", f"User requirement:\n{requirement}")

        if on_token is None:
            # Blocking path
            out = self.llm.system_user(PRD_SYSTEM, f"User requirement:\n{requirement}")
        else:
            # Streaming path
            out_chunks = []
            for chunk in self.llm.stream([sys_msg, user_msg]):
                out_chunks.append(chunk)
                on_token(chunk)
            out = "".join(out_chunks)

        msg = Message(role=self.role_name, content=out, cause_by=self.cause_by)
        pool.publish(msg)
        return msg


@dataclass
class WriteDesign:
    llm: LLM
    cause_by: str = "WriteDesign"
    role_name: str = "Architect"

    def run(self, pool: MessagePool, *, on_token=None) -> Message:
        prd = _last_of(pool, "WritePRD")
        if not prd:
            raise RuntimeError("WriteDesign requires a PRD message in the pool first.")

        sys_msg = ChatMessage("system", DESIGN_SYSTEM)
        user_msg = ChatMessage("user", f"PRD:\n{prd.content}")

        if on_token is None:
            out = self.llm.system_user(DESIGN_SYSTEM, f"PRD:\n{prd.content}")
        else:
            out_chunks = []
            for chunk in self.llm.stream([sys_msg, user_msg]):
                out_chunks.append(chunk)
                on_token(chunk)
            out = "".join(out_chunks)

        msg = Message(role=self.role_name, content=out, cause_by=self.cause_by)
        pool.publish(msg)
        return msg


@dataclass
class WriteCode:
    llm: LLM
    cause_by: str = "WriteCode"
    role_name: str = "Engineer"

    def run(self, pool: MessagePool, *, on_token=None) -> Message:
        design = _last_of(pool, "WriteDesign")
        if not design:
            raise RuntimeError("WriteCode requires a Design message in the pool first.")

        sys_msg = ChatMessage("system", CODE_SYSTEM)
        user_msg = ChatMessage("user", f"Design:\n{design.content}")

        if on_token is None:
            out = self.llm.system_user(CODE_SYSTEM, f"Design:\n{design.content}")
        else:
            out_chunks = []
            for chunk in self.llm.stream([sys_msg, user_msg]):
                out_chunks.append(chunk)
                on_token(chunk)
            out = "".join(out_chunks)

        msg = Message(role=self.role_name, content=out, cause_by=self.cause_by)
        pool.publish(msg)
        return msg


@dataclass
class WriteTest:
    llm: LLM
    cause_by: str = "WriteTest"
    role_name: str = "QA"

    def run(self, pool: MessagePool, *, on_token=None) -> Message:
        design = _last_of(pool, "WriteDesign")
        code = _last_of(pool, "WriteCode")
        if not (design and code):
            raise RuntimeError("WriteTest requires Design + Code messages in the pool first.")

        sys_msg = ChatMessage("system", TEST_SYSTEM)
        user_msg = ChatMessage("user", f"Design:\n{design.content}\n\nCode:\n{code.content}")

        if on_token is None:
            out = self.llm.system_user(
                TEST_SYSTEM,
                f"Design:\n{design.content}\n\nCode:\n{code.content}",
            )
        else:
            out_chunks = []
            for chunk in self.llm.stream([sys_msg, user_msg]):
                out_chunks.append(chunk)
                on_token(chunk)
            out = "".join(out_chunks)

        msg = Message(role=self.role_name, content=out, cause_by=self.cause_by)
        pool.publish(msg)
        return msg


# ── Action sequence (the SOP) ───────────────────────────────────────────────

DEFAULT_SOP: List[Callable] = [WritePRD, WriteDesign, WriteCode, WriteTest]
"""Default Standard Operating Procedure: PM → Architect → Engineer → QA."""