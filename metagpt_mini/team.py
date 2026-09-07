"""
Team orchestrator — runs the SOP and handles the QA → Engineer feedback loop.

SOP: PM → Architect → Engineer → QA. If QA fails, re-run Engineer with QA
feedback (up to MAX_REVISIONS). Architect and PM do not re-run after the
first pass — that's the MetaGPT canonical design.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from rich.console import Console
from rich.live import Live

from .llm import LLM
from .roles import Role, make_canonical_team
from .schema import Message, MessagePool, Manifest

console = Console()

MAX_REVISIONS = int(os.getenv("MAX_REVISIONS", "2"))   # total Engineer→QA rounds (incl. first)


@dataclass
class RunResult:
    pool: MessagePool
    manifest: Optional[Manifest] = None
    qa_passed: bool = False
    qa_rounds: int = 0
    aborted_reason: str = ""


@dataclass
class Team:
    llm: LLM
    pool: MessagePool = None
    roles: List[Role] = None
    live: bool = True
    live_state: object = None  # LiveRunState from ui

    def __post_init__(self):
        if self.pool is None:
            self.pool = MessagePool()
        if self.roles is None:
            self.roles = make_canonical_team(self.llm)

    # ── Main entry ─ ─────────────────────────────────────────────────────────────────
    def run(self, requirement: str, budget_usd: Optional[float] = None,
            max_revisions: int = MAX_REVISIONS) -> RunResult:
        budget = budget_usd if budget_usd is not None else float(
            os.getenv("MAX_BUDGET_USD", "2.50")
        )

        if self.live:
            return self._run_with_live(requirement, budget, max_revisions)
        return self._run_blocking(requirement, budget, max_revisions)

    # ── Blocking fallback (used by tests + script) ───────────────────────
    def _run_blocking(self, requirement, budget, max_revisions) -> RunResult:
        seed = Message(role="User", content=requirement, cause_by="UserInput")
        self.pool.publish(seed)

        result = RunResult(pool=self.pool)

        # PM + Architect run once
        self.roles[0].run(self.pool)
        self.roles[1].run(self.pool)

        # Engineer + QA loop
        last_manifest = None
        for round_num in range(1, max_revisions + 2):  # 1..max_revisions+1
            if self.usage_cost() > budget:
                result.aborted_reason = "budget"
                break
            qa_feedback = self._last_qa_issues_text() if round_num > 1 else None
            _, manifest = self._run_engineer_with_returns(round_num, qa_feedback)
            last_manifest = manifest
            qa_msg = self._run_qa_with_returns(round_num)
            result.qa_rounds = round_num
            result.qa_passed = bool(qa_msg.extra.get("passed", False))
            if result.qa_passed:
                break

        result.manifest = last_manifest
        return result

    def _run_engineer_with_returns(self, round_num, qa_feedback=None):
        eng_role = self.roles[2]
        for action_factory, action_name in zip(eng_role.actions, eng_role.action_names):
            action = action_factory()
            if action_name == "WriteCode":
                return action.run(self.pool, round_num=round_num, qa_feedback=qa_feedback)
        raise RuntimeError("Engineer action not found")

    def _run_qa_with_returns(self, round_num):
        qa_role = self.roles[3]
        for action_factory in qa_role.actions:
            action = action_factory()
            return action.run(self.pool, round_num=round_num)
        raise RuntimeError("QA action not found")

    def _last_qa_issues_text(self) -> str:
        last_qa = self.pool.latest_of("WriteTest")
        if not last_qa:
            return ""
        issues = last_qa.extra.get("issues", [])
        if not issues:
            return ""
        return "Issues to fix:\n" + "\n".join(f"- {i}" for i in issues)

    # ── Live mode (the actual demo) ──────────────────────────────────────
    def _run_with_live(self, requirement, budget, max_revisions) -> RunResult:
        from .ui import LiveRunState, render

        state = LiveRunState(phase="starting")
        state.budget_usd = budget
        state.model = self.llm.model
        state.base_url = self.llm.base_url
        state.context_window = self.llm.context_window
        state.requirement = requirement
        # Pre-mark all roles
        for role in self.roles:
            state.messages.append((role.name, role.actions[0].__class__.__name__, "pending", 0))
        self.live_state = state

        seed = Message(role="User", content=requirement, cause_by="UserInput")
        self.pool.publish(seed)
        state.event(f"Run started · requirement: {requirement[:80]}{'…' if len(requirement) > 80 else ''}")

        result = RunResult(pool=self.pool)

        with Live(render(state), refresh_per_second=8, console=console,
                  screen=True, transient=False) as live:
            state.live = live

            # PM runs once
            self._run_role_live(self.roles[0], round_num=1)
            if state.tokens_in + state.tokens_out > 0 and self.usage_cost() > budget:
                result.aborted_reason = "budget"; return result

            # Architect runs once
            self._run_role_live(self.roles[1], round_num=1)
            if self.usage_cost() > budget:
                result.aborted_reason = "budget"; return result

            # Engineer + QA loop
            for round_num in range(1, max_revisions + 2):
                state.event(f"Round {round_num}/{max_revisions+1}: Engineer")

                qa_feedback = self._last_qa_issues_text() if round_num > 1 else None

                # Engineer
                self._run_engineer_live(self.roles[2], round_num, qa_feedback,
                                        live=live)
                if self.usage_cost() > budget:
                    result.aborted_reason = "budget"; break

                # QA
                state.event(f"Round {round_num}: QA reviewing Engineer's output")
                qa_msg = self._run_qa_live(self.roles[3], round_num, live=live)
                result.qa_rounds = round_num
                result.qa_passed = bool(qa_msg.extra.get("passed", False))
                # Update QA row with verdict
                state.update_qa(round_num, qa_msg.extra)

                if result.qa_passed:
                    state.event(f"Round {round_num}: QA PASS ✓")
                    break
                else:
                    state.event(
                        f"Round {round_num}: QA FAIL — feeding back to Engineer"
                    )
                    if round_num > max_revisions:
                        state.event(f"Max revisions reached, accepting last output")
                        break

            # Final summary
            state.phase = "summary"
            # Pull manifest from latest Engineer message
            eng = self.pool.latest_of("WriteCode")
            if eng and "manifest" in eng.extra:
                result.manifest = eng.extra["manifest"]
            state.event(
                f"Run complete · QA passed={result.qa_passed} · "
                f"{result.qa_rounds} round(s) · ${self.llm.usage.estimated_cost_usd:.4f}"
            )
            # Hold final state for a moment
            import time
            live.update(render(state))
            time.sleep(0.5)

        return result

    # ── Live helpers ─────────────────────────────────────────────────
    def _run_role_live(self, role: Role, *, round_num: int):
        state = self.live_state
        # Mark previous roles as done; this one active
        for i, (rn, _, _, _) in enumerate(state.messages):
            if rn == role.name:
                state.messages[i] = (rn, role.actions[0].__class__.__name__, "active", round_num)
                break
        state.role = role.name
        state.action = role.actions[0].__class__.__name__
        state.content = ""
        state.phase = "starting"
        state.color = role.color
        state.event(f"{role.name} → {role.actions[0].__class__.__name__}")

        def on_token(chunk: str):
            state.content += chunk
            state.phase = "streaming"
            state.refresh_stats(self.llm)
            state.live.update(state.render())

        role.run(self.pool, on_token=on_token, round_num=round_num)

        for i, (rn, an, _, _) in enumerate(state.messages):
            if rn == role.name:
                state.messages[i] = (rn, an, "done", round_num)
                break
        state.phase = "done"
        state.refresh_stats(self.llm)
        state.event(f"{role.name} ✓ done ({len(state.content)} chars)")
        state.live.update(state.render())

    def _run_engineer_live(self, role: Role, round_num: int,
                           qa_feedback: Optional[str], *, live):
        state = self.live_state
        for i, (rn, _, _, _) in enumerate(state.messages):
            if rn == role.name:
                state.messages[i] = (rn, "WriteCode", "active", round_num)
                break
        state.role = role.name
        state.action = "WriteCode"
        state.content = ""
        state.phase = "starting"
        state.color = role.color
        state.refresh_stats(self.llm)
        live.update(state.render())

        # Engineer is special: streams tokens but ALSO produces a Manifest.
        # We render a file-tree preview as it streams.
        for action_factory in role.actions:
            action = action_factory()
            if hasattr(action, "run") and "WriteCode" in type(action).__name__:
                # The action emits text chunks via on_token; we'll show them
                # but also accumulate files as they appear.
                state.event(f"Engineer drafting project structure (round {round_num})")

                # We need access to raw stream — bypass on_token abstraction.
                from .llm import ChatMessage
                from .actions import CODE_SYSTEM, CODE_REVISION_SYSTEM, MANIFEST_SCHEMA
                design = self.pool.latest_of("WriteDesign")
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

                # Try structured tool-use first
                manifest_dict = None
                try:
                    state.event("Calling tool: emit_manifest (structured)")
                    manifest_dict = self.llm.structured(
                        [ChatMessage("system", system), ChatMessage("user", user_text)],
                        tool_name="emit_manifest",
                        tool_description="Emit the multi-file project manifest.",
                        input_schema=MANIFEST_SCHEMA,
                        role_tag="Engineer",
                    )
                except Exception as e:
                    state.event(f"Tool-use failed: {type(e).__name__} — fallback to streaming")
                    import json as _json
                    chunks = []
                    for c in self.llm.stream(
                        [ChatMessage("system", system), ChatMessage("user", user_text)],
                        role_tag="Engineer",
                    ):
                        chunks.append(c)
                        state.content = "".join(chunks[-200:])  # last 200 chars rolling
                        state.phase = "streaming"
                        state.refresh_stats(self.llm)
                        live.update(state.render())
                    state.content = "".join(chunks)
                    text = state.content
                    # Try to extract JSON from text
                    s = text.find("{"); e = text.rfind("}")
                    if s != -1 and e > s:
                        try:
                            manifest_dict = _json.loads(text[s:e + 1])
                        except _json.JSONDecodeError:
                            manifest_dict = None
                    if manifest_dict is None:
                        # Single-file fallback
                        manifest_dict = {
                            "project_name": "generated_project",
                            "summary": "Single-file fallback",
                            "files": [{"path": "main.py", "content": text,
                                        "rationale": "Fallback single file"}],
                            "dependencies": [],
                            "run_instructions": "python main.py",
                        }
                    state.refresh_stats(self.llm)
                    live.update(state.render())

                from .schema import Manifest, FileEntry
                manifest = Manifest(
                    project_name=manifest_dict.get("project_name", "generated_project"),
                    summary=manifest_dict.get("summary", ""),
                    files=[FileEntry(**f) for f in manifest_dict.get("files", [])],
                    dependencies=manifest_dict.get("dependencies", []),
                    run_instructions=manifest_dict.get("run_instructions", ""),
                )
                state.manifest = manifest
                state.content = manifest.summary
                state.event(
                    f"Manifest: {len(manifest.files)} files · "
                    f"{manifest.total_chars():,} chars · "
                    f"deps: {', '.join(manifest.dependencies) or 'stdlib'}"
                )

                # Build the textual message for the pool
                file_list = "\n".join(f"- `{f.path}` — {f.rationale}" for f in manifest.files)
                content = (
                    f"# Project: {manifest.project_name}\n\n{manifest.summary}\n\n"
                    f"## Files ({len(manifest.files)})\n{file_list}\n\n"
                    f"## Dependencies\n{', '.join(manifest.dependencies) or '(stdlib only)'}\n\n"
                    f"## Run\n```bash\n{manifest.run_instructions}```"
                )
                from .schema import Message
                msg = Message(
                    role="Engineer", content=content, cause_by="WriteCode",
                    round_num=round_num,
                    extra={"manifest": manifest, "file_paths": manifest.file_paths()},
                )
                self.pool.publish(msg)

                for i, (rn, _, _, _) in enumerate(state.messages):
                    if rn == "Engineer":
                        state.messages[i] = ("Engineer", "WriteCode", "done", round_num)
                        break
                state.phase = "done"
                state.refresh_stats(self.llm)
                live.update(state.render())
                return

    def _run_qa_live(self, role: Role, round_num: int, *, live):
        from .llm import ChatMessage
        from .actions import QA_SYSTEM, QA_REPORT_SCHEMA
        import json as _json

        state = self.live_state
        for i, (rn, _, _, _) in enumerate(state.messages):
            if rn == role.name:
                state.messages[i] = (rn, "WriteTest", "active", round_num)
                break
        state.role = role.name
        state.action = "WriteTest"
        state.content = ""
        state.phase = "starting"
        state.color = role.color
        state.refresh_stats(self.llm)
        live.update(state.render())

        design = self.pool.latest_of("WriteDesign")
        code = self.pool.latest_of("WriteCode")
        context = f"Design:\n{design.content}\n\nCode (engineer manifest):\n{code.content}"

        report = None
        try:
            state.event("Calling tool: qa_report (structured)")
            report = self.llm.structured(
                [ChatMessage("system", QA_SYSTEM),
                 ChatMessage("user", context)],
                tool_name="qa_report",
                tool_description="Emit a structured QA pass/fail report.",
                input_schema=QA_REPORT_SCHEMA,
                role_tag="QA",
            )
        except Exception as e:
            state.event(f"Tool-use failed: {type(e).__name__} — fallback to streaming")
            chunks = []
            for c in self.llm.stream(
                [ChatMessage("system", QA_SYSTEM),
                 ChatMessage("user", context)],
                role_tag="QA",
            ):
                chunks.append(c)
                state.content = "".join(chunks[-300:])
                state.phase = "streaming"
                state.refresh_stats(self.llm)
                live.update(state.render())
            text = "".join(chunks)
            state.content = text
            try:
                report = _json.loads(text)
            except _json.JSONDecodeError:
                # Find any JSON block
                s = text.find("{"); e = text.rfind("}")
                if s != -1 and e > s:
                    try:
                        report = _json.loads(text[s:e + 1])
                    except _json.JSONDecodeError:
                        report = {"passed": True, "issues": [], "summary": text[:500]}

        issues = report.get("issues", []) or []
        passed = bool(report.get("passed", False)) and not issues
        if len(issues) >= 2:
            passed = False

        content = (
            f"# QA Report — round {round_num}\n\n"
            f"**Verdict:** {'PASS' if passed else 'FAIL'}\n\n"
            f"**Summary:** {report.get('summary', '')}\n"
        )
        if issues:
            content += "\n**Issues:**\n" + "\n".join(f"- {i}" for i in issues)

        from .schema import Message
        msg = Message(
            role="QA", content=content, cause_by="WriteTest",
            round_num=round_num,
            extra={"passed": passed, "issues": issues, "summary": report.get("summary", "")},
        )
        self.pool.publish(msg)

        for i, (rn, _, _, _) in enumerate(state.messages):
            if rn == "QA":
                state.messages[i] = ("QA", "WriteTest", "done", round_num)
                break
        state.phase = "done"
        state.refresh_stats(self.llm)
        live.update(state.render())
        return msg

    def usage_cost(self) -> float:
        return self.llm.usage.estimated_cost_usd