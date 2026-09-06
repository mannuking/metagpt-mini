"""
Team — the orchestrator. Owns the MessagePool, holds the Roles, runs them in
order, and surfaces the cost / log to the caller.

Supports two modes:
- verbose=True:  rich panel-by-panel output, blocking
- live=True:    beautiful real-time UI with streaming tokens
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, List, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel

from .llm import LLM
from .roles import Role, make_canonical_team
from .schema import Message, MessagePool

console = Console()


@dataclass
class Team:
    llm: LLM
    pool: MessagePool = None
    roles: List[Role] = None
    verbose: bool = False
    live: bool = False

    def __post_init__(self):
        if self.pool is None:
            self.pool = MessagePool()
        if self.roles is None:
            self.roles = make_canonical_team(self.llm)

    def run(self, requirement: str, budget_usd: Optional[float] = None) -> MessagePool:
        """Execute the SOP for the given requirement. Returns the populated pool."""
        budget = budget_usd if budget_usd is not None else float(
            os.getenv("MAX_BUDGET_USD", "2.50")
        )

        if self.live:
            return self._run_live(requirement, budget)
        return self._run_verbose(requirement, budget)

    # ── Verbose (blocking) mode ───────────────────────────────────
    def _run_verbose(self, requirement: str, budget: float) -> MessagePool:
        from rich.rule import Rule
        from rich.panel import Panel

        if self.verbose:
            console.print(Panel.fit(
                f"[bold cyan]MetaGPT-Mini[/bold cyan]  model=[yellow]{self.llm.model}[/yellow]\n"
                f"requirement: [italic]{requirement}[/italic]\n"
                f"budget: [red]${budget:.2f}[/red]",
                title="Start",
            ))

        seed = Message(role="User", content=requirement, cause_by="UserInput")
        self.pool.publish(seed)

        for role in self.roles:
            if self.usage_cost() > budget:
                if self.verbose:
                    console.print(f"[red]Budget ${budget:.2f} exceeded — stopping early.[/red]")
                break
            if self.verbose:
                console.rule(f"[bold magenta]{role.name}[/bold magenta] — {role.profile}")
            for msg in role.run(self.pool):
                if self.verbose:
                    console.print(Panel(
                        msg.content[:1500] + ("\n…" if len(msg.content) > 1500 else ""),
                        title=f"[green]{role.name}[/green] → {msg.cause_by}",
                        subtitle=f"msg_id={msg.msg_id}",
                        border_style="green",
                    ))

        if self.verbose:
            u = self.llm.usage
            console.print(Panel.fit(
                f"[bold]Run complete[/bold]\n"
                f"calls: {u.calls}  ·  tokens: {u.total_tokens:,} (in {u.prompt_tokens:,} / out {u.completion_tokens:,})\n"
                f"elapsed: {u.elapsed_s:.1f}s  ·  est. cost: [red]${u.estimated_cost_usd:.4f}[/red]",
                title="Summary",
                border_style="cyan",
            ))
        return self.pool

    # ── Beautiful live mode (for the class demo) ──────────────────
    def _run_live(self, requirement: str, budget: float) -> MessagePool:
        from .ui import LiveRunState, render

        # Pre-mark all roles as pending
        state = LiveRunState(phase="starting")
        for role in self.roles:
            action_name = role.action_names[0] if role.action_names else ""
            state.messages.append((role.name, action_name, "pending"))

        seed = Message(role="User", content=requirement, cause_by="UserInput")
        self.pool.publish(seed)

        with Live(render(state), refresh_per_second=10, screen=False,
                  console=console, transient=False) as live:
            for role in self.roles:
                if self.usage_cost() > budget:
                    state.phase = "stopped"
                    live.update(render(state))
                    break

                # Mark previous roles as done
                for i, (rn, _, _) in enumerate(state.messages):
                    if rn == role.name:
                        state.messages[i] = (rn, role.action_names[0], "active")
                        break

                state.role = role.name
                state.action = role.action_names[0]
                state.content = ""
                state.phase = "starting"
                state.tokens_in = self.llm.usage.prompt_tokens
                state.tokens_out = self.llm.usage.completion_tokens
                state.cost_usd = self.llm.usage.estimated_cost_usd
                state.elapsed_s = self.llm.usage.elapsed_s
                live.update(render(state))

                # Streaming callback
                def on_token(chunk: str, _r=role):
                    state.content += chunk
                    state.tokens_in = self.llm.usage.prompt_tokens
                    state.tokens_out = self.llm.usage.completion_tokens
                    state.cost_usd = self.llm.usage.estimated_cost_usd
                    state.elapsed_s = self.llm.usage.elapsed_s
                    state.phase = "streaming"
                    live.update(render(state))

                role.run(self.pool, on_token=on_token)

                # Mark done
                for i, (rn, an, _) in enumerate(state.messages):
                    if rn == role.name:
                        state.messages[i] = (rn, an, "done")
                        break
                state.phase = "done"
                state.tokens_in = self.llm.usage.prompt_tokens
                state.tokens_out = self.llm.usage.completion_tokens
                state.cost_usd = self.llm.usage.estimated_cost_usd
                state.elapsed_s = self.llm.usage.elapsed_s
                live.update(render(state))

            # Final summary
            u = self.llm.usage
            state.phase = "summary"
            state.role = "✓"
            state.action = "complete"
            state.content = (
                f"calls: {u.calls}  ·  tokens: {u.total_tokens:,}\n"
                f"elapsed: {u.elapsed_s:.1f}s  ·  est. cost: ${u.estimated_cost_usd:.4f}"
            )
            live.update(render(state))

        return self.pool

    def usage_cost(self) -> float:
        return self.llm.usage.estimated_cost_usd