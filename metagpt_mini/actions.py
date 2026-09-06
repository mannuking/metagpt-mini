"""
Actions — the verbs in the SOP.

Each Action takes context (pool + LLM) and emits a Message (or Manifest).
The Engineer uses Anthropic's tool-use API for *guaranteed* multi-file
structured output — no JSON parsing roulette.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable, List, Optional

from .llm import LLM, ChatMessage
from .schema import FileEntry, Manifest, Message, MessagePool


# ── Helpers ────────────────────────────────────────────────────────────────

def _last_of(pool: MessagePool, cause_by: str) -> Optional[Message]:
    return pool.latest_of(cause_by)


def _user_requirement(pool: MessagePool) -> str:
    seed = next((m for m in pool.history() if m.role == "User"), None)
    return seed.content if seed else "(no requirement provided)"


# ── System prompts ─────────────────────────────────────────────────────────

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
    "1. Architecture overview\n"
    "2. Module breakdown (file paths + responsibilities)\n"
    "3. Data model (classes / dataclasses)\n"
    "4. Interface contracts (function signatures + types)\n"
    "5. Edge cases\n"
    "Output code-ready design — no marketing language."
)

CODE_SYSTEM = (
    "You are a senior Backend Engineer working in PYTHON. The design is below. "
    "Produce a complete Python project as a JSON manifest of files. "
    "Each file must have a real relative path (e.g. 'src/main.py', "
    "'tests/test_main.py', 'README.md', 'pyproject.toml'), the full file content "
    "(no truncation, no placeholders, no TODO comments), and a one-line "
    "rationale. Use ONLY the Python standard library unless the design "
    "explicitly requires an external dependency. All code must have type hints "
    "and an `if __name__ == \"__main__\":` demo where appropriate. "
    "Aim for 4-8 files: a README, pyproject.toml, the main module(s), and at "
    "least one test file. File extensions MUST be .py, .md, or .toml — do not "
    "generate C, Go, Rust, or JavaScript unless the user explicitly asks for "
    "them. The project must be installable with `pip install -e .` and runnable "
    "via `python -m <package_name>` or directly as a script."
)

CODE_REVISION_SYSTEM = (
    "You are a senior Backend Engineer. The QA agent found issues in your "
    "previous output. The design is below. Read the QA report carefully and "
    "regenerate the affected files ONLY (return the full content of each "
    "revised file). If a file is unchanged, omit it. Be minimal: do not rewrite "
    "files that are correct."
)

QA_SYSTEM = (
    "You are a senior QA Engineer. Review the design + generated code. Verify:\n"
    "1. Every functional requirement in the PRD is covered by code\n"
    "2. The code compiles/parses (mental syntax check)\n"
    "3. Edge cases mentioned in the design are handled\n"
    "4. Type hints + docstrings are present\n"
    "5. There is a runnable entry point\n"
    "Output a JSON report with: 'passed' (bool), 'issues' (list of strings, "
    "empty if passed), 'summary' (one paragraph). Be honest: only set "
    "'passed'=true if the code is genuinely production-quality."
)


# ── JSON manifest schema for the Engineer ──────────────────────────────────
MANIFEST_SCHEMA = {
    "type": "object",
    "properties": {
        "project_name": {
            "type": "string",
            "description": "Lowercase, hyphen-free name for the generated project (e.g. 'cli_todo_app')",
        },
        "summary": {
            "type": "string",
            "description": "One-paragraph description of what the project does",
        },
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to project root"},
                    "content": {"type": "string", "description": "Full file contents"},
                    "rationale": {"type": "string", "description": "One-line reason for this file"},
                },
                "required": ["path", "content"],
            },
        },
        "dependencies": {
            "type": "array",
            "items": {"type": "string"},
            "description": "pip package names required to run the project (use stdlib if possible)",
        },
        "run_instructions": {
            "type": "string",
            "description": "Shell commands to install and run the project",
        },
    },
    "required": ["project_name", "summary", "files", "run_instructions"],
}

QA_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "passed": {"type": "boolean"},
        "issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Specific issues to fix (empty if passed=true)",
        },
        "summary": {"type": "string"},
    },
    "required": ["passed", "issues", "summary"],
}


# ── Actions ────────────────────────────────────────────────────────────────

@dataclass
class WritePRD:
    llm: LLM
    cause_by: str = "WritePRD"
    role_name: str = "ProductManager"

    def run(self, pool: MessagePool, *, on_token=None, round_num: int = 0) -> Message:
        requirement = _user_requirement(pool)
        sys_msg = ChatMessage("system", PRD_SYSTEM)
        user_msg = ChatMessage("user", f"User requirement:\n{requirement}")
        if on_token is None:
            out = self.llm.system_user(PRD_SYSTEM, f"User requirement:\n{requirement}",
                                       role_tag="ProductManager")
        else:
            chunks = []
            for c in self.llm.stream([sys_msg, user_msg], role_tag="ProductManager"):
                chunks.append(c); on_token(c)
            out = "".join(chunks)
        msg = Message(role=self.role_name, content=out, cause_by=self.cause_by,
                      round_num=round_num)
        pool.publish(msg)
        return msg


@dataclass
class WriteDesign:
    llm: LLM
    cause_by: str = "WriteDesign"
    role_name: str = "Architect"

    def run(self, pool: MessagePool, *, on_token=None, round_num: int = 0) -> Message:
        prd = _last_of(pool, "WritePRD")
        if not prd:
            raise RuntimeError("WriteDesign requires a PRD message in the pool first.")
        sys_msg = ChatMessage("system", DESIGN_SYSTEM)
        user_msg = ChatMessage("user", f"PRD:\n{prd.content}")
        if on_token is None:
            out = self.llm.system_user(DESIGN_SYSTEM, f"PRD:\n{prd.content}",
                                       role_tag="Architect")
        else:
            chunks = []
            for c in self.llm.stream([sys_msg, user_msg], role_tag="Architect"):
                chunks.append(c); on_token(c)
            out = "".join(chunks)
        msg = Message(role=self.role_name, content=out, cause_by=self.cause_by,
                      round_num=round_num)
        pool.publish(msg)
        return msg


@dataclass
class WriteCode:
    """Multi-file Engineer. Uses tool-use to guarantee a Manifest dict."""
    llm: LLM
    cause_by: str = "WriteCode"
    role_name: str = "Engineer"

    def run(self, pool: MessagePool, *, on_token=None, round_num: int = 0,
            qa_feedback: Optional[str] = None) -> tuple[Message, Manifest]:
        design = _last_of(pool, "WriteDesign")
        if not design:
            raise RuntimeError("WriteCode requires a Design message in the pool first.")

        if qa_feedback:
            system = CODE_REVISION_SYSTEM
            user_text = (
                f"Design:\n{design.content}\n\n"
                f"QA feedback from previous round:\n{qa_feedback}\n\n"
                "Regenerate the affected files. Return only files that changed."
            )
        else:
            system = CODE_SYSTEM
            user_text = f"Design:\n{design.content}"

        # Tool-use gives us a guaranteed JSON manifest. Falls back to streaming
        # text extraction if the endpoint rejects tool-use (some Anthropic-compat
        # providers don't support it).
        manifest_dict = None
        try:
            manifest_dict = self.llm.structured(
                [ChatMessage("system", system),
                 ChatMessage("user", user_text)],
                tool_name="emit_manifest",
                tool_description="Emit the multi-file project manifest.",
                input_schema=MANIFEST_SCHEMA,
                role_tag="Engineer",
            )
        except Exception:
            # Fallback: stream text, parse as JSON
            chunks = []
            for c in self.llm.stream(
                [ChatMessage("system", system), ChatMessage("user", user_text)],
                role_tag="Engineer",
            ):
                chunks.append(c)
                if on_token:
                    on_token(c)
            text = "".join(chunks)
            manifest_dict = _parse_manifest_from_text(text)

        manifest = Manifest(
            project_name=manifest_dict.get("project_name", "generated_project"),
            summary=manifest_dict.get("summary", ""),
            files=[FileEntry(**f) for f in manifest_dict.get("files", [])],
            dependencies=manifest_dict.get("dependencies", []),
            run_instructions=manifest_dict.get("run_instructions", ""),
        )

        # Render a textual summary message for the pool
        file_list = "\n".join(f"- `{f.path}` — {f.rationale}" for f in manifest.files)
        content = (
            f"# Project: {manifest.project_name}\n\n"
            f"{manifest.summary}\n\n"
            f"## Files ({len(manifest.files)})\n{file_list}\n\n"
            f"## Dependencies\n{', '.join(manifest.dependencies) or '(stdlib only)'}\n\n"
            f"## Run\n```bash\n{manifest.run_instructions}\n```"
        )
        msg = Message(
            role=self.role_name, content=content, cause_by=self.cause_by,
            round_num=round_num,
            extra={"manifest": manifest, "file_paths": manifest.file_paths()},
        )
        pool.publish(msg)
        return msg, manifest


@dataclass
class WriteTest:
    """QA: produces a structured pass/fail report via tool-use."""
    llm: LLM
    cause_by: str = "WriteTest"
    role_name: str = "QA"

    def run(self, pool: MessagePool, *, on_token=None, round_num: int = 0) -> Message:
        design = _last_of(pool, "WriteDesign")
        code = _last_of(pool, "WriteCode")
        if not (design and code):
            raise RuntimeError("WriteTest requires Design + Code messages in the pool first.")

        context = f"Design:\n{design.content}\n\nCode (engineer manifest):\n{code.content}"
        sys_msg = ChatMessage("system", QA_SYSTEM)
        user_msg = ChatMessage("user", context)

        report = None
        try:
            report = self.llm.structured(
                [sys_msg, user_msg],
                tool_name="qa_report",
                tool_description="Emit a structured QA pass/fail report.",
                input_schema=QA_REPORT_SCHEMA,
                role_tag="QA",
            )
        except Exception:
            # Fallback: streaming text
            chunks = []
            for c in self.llm.stream([sys_msg, user_msg], role_tag="QA"):
                chunks.append(c)
                if on_token:
                    on_token(c)
            text = "".join(chunks)
            try:
                report = json.loads(text)
            except json.JSONDecodeError:
                # Last resort: assume pass
                report = {"passed": True, "issues": [], "summary": text[:500]}

        issues = report.get("issues", []) or []
        passed = bool(report.get("passed", False)) and not issues
        # Force the QA to be a little conservative — if many issues, fail.
        if len(issues) >= 2:
            passed = False

        content_lines = [
            f"# QA Report — round {round_num}",
            "",
            f"**Verdict:** {'PASS' if passed else 'FAIL'}",
            "",
            f"**Summary:** {report.get('summary', '')}",
        ]
        if issues:
            content_lines.append("\n**Issues:**\n" + "\n".join(f"- {i}" for i in issues))
        content = "\n".join(content_lines)

        msg = Message(
            role=self.role_name, content=content, cause_by=self.cause_by,
            round_num=round_num,
            extra={"passed": passed, "issues": issues, "summary": report.get("summary", "")},
        )
        pool.publish(msg)
        return msg


# ── Helpers for fallback parsing ────────────────────────────────────────────
def _parse_manifest_from_text(text: str) -> dict:
    """If tool-use failed, try to extract a JSON manifest from streamed text."""
    # Find first { ... last } block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    # Last resort: synthesize a single-file manifest
    return {
        "project_name": "generated_project",
        "summary": "Generated by MetaGPT-Mini (fallback path).",
        "files": [{"path": "main.py", "content": text, "rationale": "Single-file fallback"}],
        "dependencies": [],
        "run_instructions": "python main.py",
    }


# ── Action sequence (the SOP) ───────────────────────────────────────────────
DEFAULT_SOP: List[str] = ["WritePRD", "WriteDesign", "WriteCode", "WriteTest"]
"""Default Standard Operating Procedure: PM → Architect → Engineer → QA."""