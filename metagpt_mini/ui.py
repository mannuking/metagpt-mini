"""
Beautiful live UI for the MetaGPT-Mini class demo.

Renders an animated, real-time visualization of the 4-agent SOP:
- Per-role banners with live spinners
- Token-by-token streaming as the LLM emits
- Cost + token counter that updates in real time
- Final summary panel

Designed to be projected on a classroom screen — big, colorful, readable.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    TimeElapsedColumn, TaskProgressColumn,
)
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.align import Align
from rich import box

console = Console()

ROLE_COLORS = {
    "ProductManager": "cyan",
    "Architect":      "magenta",
    "Engineer":       "green",
    "QA":             "yellow",
    "User":           "white",
}

ACTION_VERBS = {
    "WritePRD":    "drafting PRD",
    "WriteDesign": "writing design",
    "WriteCode":   "generating code",
    "WriteTest":   "writing tests",
}

BANNER_ART = r"""
[bold cyan]
   __  __          _ _      _____         _
  |  \/  | ___  __| (_) ___|  __ \___  __| |_   _ _ __ ___
  | |\/| |/ _ \/ _` | |/ _ \  |__) / _ \/ _` | | | | '_ ` _ \
  | |  | |  __/ (_| | |  __/  ___/  __/ (_| | |_| | | | | | |
  |_|  |_|\___|\__,_|_|\___|_|   \___|\__,_|\__,_|_| |_| |_|
[/bold cyan]
[dim]ICLR 2024 Oral · #1 LLM-Agent · LLM-agnostic reimplementation[/dim]
"""


@dataclass
class LiveRunState:
    """Mutable state shared across the live UI."""
    role: str = ""
    action: str = ""
    phase: str = "starting"   # starting | streaming | done
    content: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    elapsed_s: float = 0.0
    cost_usd: float = 0.0
    messages: list = None  # list of (role, action, status) tuples

    def __post_init__(self):
        if self.messages is None:
            self.messages = []


def _role_panel(state: LiveRunState) -> Panel:
    """The main panel showing current role + streaming content."""
    if not state.role:
        return Panel("Initializing...", title="MetaGPT-Mini", border_style="cyan")

    color = ROLE_COLORS.get(state.role, "white")
    verb = ACTION_VERBS.get(state.action, state.action)

    if state.phase == "starting":
        body = f"[bold {color}]{state.role}[/bold {color}] [dim]is {verb}...[/dim]"
    elif state.phase == "streaming":
        # Show last 12 lines so the panel doesn't overflow
        lines = state.content.split("\n")
        body_lines = lines[-12:]
        truncated = len(lines) > 12
        body = Text()
        if truncated:
            body.append(f"[... {len(lines) - 12} earlier lines ...]\n", style="dim")
        body.append("\n".join(body_lines))
    else:  # done
        lines = state.content.split("\n")
        body = Text("\n".join(lines[-15:]))

    return Panel(
        body,
        title=f"[bold {color}]{state.role}[/bold {color}] [dim]->[/dim] [bold]{state.action}[/bold]",
        subtitle=f"[dim]{state.tokens_in + state.tokens_out:,} tokens  ·  ${state.cost_usd:.4f}[/dim]",
        border_style=color,
        box=box.ROUNDED,
    )


def _progress_table(state: LiveRunState) -> Table:
    """A small table at the bottom showing per-role status."""
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Role", style="bold")
    table.add_column("Action")
    table.add_column("Status")

    for role, action, status in state.messages:
        color = ROLE_COLORS.get(role, "white")
        if status == "done":
            sym = "[bold green]✓[/bold green]"
        elif status == "active":
            sym = "[bold yellow]●[/bold yellow]"
        else:
            sym = "[dim]○[/dim]"
        table.add_row(
            f"[{color}]{role}[/{color}]",
            action or "—",
            f"{sym} {status}",
        )
    return table


def _stats_table(state: LiveRunState) -> Table:
    """Live token + cost counter."""
    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    t.add_column("Metric", style="bold")
    t.add_column("Value", justify="right")
    t.add_row("Tokens in",  f"{state.tokens_in:,}")
    t.add_row("Tokens out", f"{state.tokens_out:,}")
    t.add_row("Elapsed",    f"{state.elapsed_s:.1f}s")
    t.add_row("Est. cost",  f"[bold]${state.cost_usd:.4f}[/bold]")
    return t


def make_live_layout(state: LiveRunState) -> Layout:
    """The full screen layout for the live demo."""
    layout = Layout()
    layout.split_column(
        Layout(name="banner", size=8),
        Layout(name="main",   ratio=1),
        Layout(name="footer", size=12),
    )
    layout["main"].split_row(
        Layout(name="role_panel", ratio=2),
        Layout(name="stats",      size=32),
    )
    layout["footer"].split_column(
        Layout(name="progress_table"),
        Layout(name="rule", size=1),
    )
    return layout


def render(state: LiveRunState) -> Layout:
    layout = make_live_layout(state)
    layout["banner"].update(Panel(BANNER_ART, box=box.DOUBLE, border_style="cyan"))
    layout["role_panel"].update(_role_panel(state))
    layout["stats"].update(Panel(_stats_table(state), title="[bold]Stats[/bold]",
                                  border_style="cyan", box=box.ROUNDED))
    layout["progress_table"].update(_progress_table(state))
    layout["rule"].update(Rule(style="cyan"))
    return layout