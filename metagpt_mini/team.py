"""
Team — the orchestrator. Owns the MessagePool, holds the Roles, runs them in
order, and surfaces the cost / log to the caller.

This is what MetaGPT calls "Environment + Team" in §3.4 of the paper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from rich.console import Console
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
    verbose: bool = True

    def __post_init__(self):
        if self.pool is None:
            self.pool = MessagePool()
        if self.roles is None:
            self.roles = make_canonical_team(self.llm)

    # ── The run loop ────────────────────────────────────────────
    def run(self, requirement: str, budget_usd: Optional[float] = None) -> MessagePool:
        """Execute the SOP for the given requirement. Returns the populated pool."""
        budget = budget_usd if budget_usd is not None else float(
            __import__("os").getenv("MAX_BUDGET_USD", "0.50")
        )

        if self.verbose:
            console.print(Panel.fit(
                f"[bold cyan]MetaGPT-Mini[/bold cyan]  model=[yellow]{self.llm.model}[/yellow]\n"
                f"requirement: [italic]{requirement}[/italic]\n"
                f"budget: [red]${budget:.2f}[/red]",
                title="Start",
            ))

        # Seed the pool with the user requirement as a synthetic "User" message.
        seed = Message(role="User", content=requirement, cause_by="UserInput")
        self.pool.publish(seed)

        # Run each role in canonical SOP order.
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
                f"elapsed: {u.elapsed_s:.1f}s  ·  est. cost: [red]${u.estimated_cost_usd:.3f}[/red]",
                title="Summary",
                border_style="cyan",
            ))

        return self.pool

    def usage_cost(self) -> float:
        return self.llm.usage.estimated_cost_usd