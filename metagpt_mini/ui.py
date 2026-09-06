"""
Beautiful full-screen TUI for MetaGPT-Mini's live class demo.

Layout (top-down, all regions responsive to terminal size):

  ┌──────────────────────────────────────────────────────────────────────────┐
  │ BANNER       (pyfiglet "MetaGPT-Mini" wordmark + ICLR Oral footer)       │  size=9
  ├──────────────────────────────────────┬───────────────────────────────────┤
  │ ROLE PANEL   (current role streaming)│ STATS PANEL                       │
  │              (reflows on resize)      │ (model, URL, ctx, tokens,         │  ratio=2
  │                                       │  cost, ETA, throughput,           │
  │                                       │  per-role breakdown)              │
  ├──────────────────────────────────────┴───────────────────────────────────┤
  │ PROGRESS TABLE   (4 roles × action × round × status)                     │  size=5
  ├──────────────────────────────────────────────────────────────────────────┤
  │ EVENT LOG (scrolling, color-coded, timestamped)                          │  size=10
  ├──────────────────────────────────────────────────────────────────────────┤
  │ REAL-WORLD APPS SIDEBAR (MetaGPT, Cursor, Devin, CrewAI, AutoGen, …)    │  size=3
  └──────────────────────────────────────────────────────────────────────────┘

Resizes gracefully: footer regions are always-visible, main area absorbs the rest.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.align import Align
from rich import box
from rich.rule import Rule
from rich.console import Group as RichGroup

from .llm import LLMUsage

console = Console()

# ── Banner (pyfiglet — renders cleanly in any width) ───────────────────────
def _make_banner(width: int = 80) -> str:
    """Generate the MetaGPT-Mini banner with pyfiglet. Falls back to plain text."""
    try:
        import pyfiglet
        # 'slant' is the cleanest 6-line font for MetaGPT-Mini
        art = pyfiglet.figlet_format("MetaGPT-Mini", font="slant")
        return art.rstrip()
    except Exception:
        # Fallback if pyfiglet not installed
        return (
            "  __  __          _ _      _____         _   \n"
            " |  \\/  | ___  __| (_) ___|  __ \\___  __| |_ \n"
            " | |\\/| |/ _ \\/ _` | |/ _ \\ |__) / _ \\/ _` | |\n"
            " | |  | |  __/ (_| | |  __/  __/  __/ (_| | |\n"
            " |_|  |_|\\___|\\__,_|_|\\___|_|   \\___|\\__,_|_|\n"
        )


BANNER_ART = _make_banner()
BANNER_HEIGHT_LINES = BANNER_ART.count("\n") + 1

# ── Colors ────────────────────────────────────────────────────────────────
ROLE_COLORS = {
    "ProductManager": "cyan",
    "Architect":      "magenta",
    "Engineer":       "green",
    "QA":             "yellow",
    "User":           "white",
}

ROLE_PROFILES = {
    "ProductManager": "Senior PM · drafts PRD",
    "Architect":      "Senior Architect · designs system",
    "Engineer":       "Senior Engineer · implements project",
    "QA":             "Senior QA · reviews & loops feedback",
}

# ── Real-world apps that use SOP-style multi-agent orchestration ─────────
REAL_WORLD_APPS = [
    "MetaGPT · geekan/MetaGPT (50k★) · the paper we're reimplementing",
    "Cursor · cursor.sh · SOP for code agents",
    "Devin · Cognition Labs · autonomous SWE",
    "AutoGen · microsoft/autogen (35k★) · multi-agent",
    "CrewAI · crewAIInc/crewAI · role-based teams",
    "LangGraph · langchain-ai/langgraph · graph orchestration",
]

ICLR_FOOTER = (
    "ICLR 2024 Oral · top 1.2% · ranked #1 LLM-Agent · "
    "MetaGPT: 3.6× quality, 10× cheaper than GPT-4 single-agent on HumanEval"
)


@dataclass
class Event:
    ts: float
    level: str   # "info" | "ok" | "warn" | "err" | "token"
    msg: str

    def __str__(self) -> str:
        ts = time.strftime("%H:%M:%S", time.localtime(self.ts))
        return f"[{ts}] {self.msg}"


@dataclass
class LiveRunState:
    """Mutable state shared between Team and UI."""
    requirement: str = ""
    model: str = ""
    base_url: str = ""
    context_window: int = 0
    budget_usd: float = 0.0

    role: str = ""
    action: str = ""
    color: str = "white"
    phase: str = "starting"      # starting | streaming | done | summary | stopped
    content: str = ""

    manifest: object = None       # metagpt_mini.schema.Manifest
    test_result: object = None    # pytest result

    # messages: list of (role, action, status, round_num)
    messages: list = field(default_factory=list)

    # Per-role token + cost tracking (filled from llm.usage.log)
    role_tokens_in: dict = field(default_factory=dict)
    role_tokens_out: dict = field(default_factory=dict)
    role_cost_usd: dict = field(default_factory=dict)

    # Tokens-in-flight (during streaming)
    tokens_in: int = 0
    tokens_out: int = 0
    elapsed_s: float = 0.0
    cost_usd: float = 0.0

    # Event log (max 50 events)
    events: deque = field(default_factory=lambda: deque(maxlen=50))

    # Live handle (set by Team._run_with_live)
    live: object = None

    # ── Event helpers ──────────────────────────────────────
    def event(self, msg: str, level: str = "info"):
        e = Event(ts=time.time(), level=level, msg=msg)
        self.events.append(e)

    def update_qa(self, round_num: int, extra: dict):
        passed = extra.get("passed", False)
        new_status = "passed" if passed else "failed"
        for i, (rn, an, st, rd) in enumerate(self.messages):
            if rn == "QA":
                self.messages[i] = (rn, an, new_status, round_num)
                break

    def refresh_stats(self, llm):
        u = llm.usage
        self.tokens_in = u.prompt_tokens
        self.tokens_out = u.completion_tokens
        self.elapsed_s = u.elapsed_s
        self.cost_usd = u.estimated_cost_usd

        self.role_tokens_in = {}
        self.role_tokens_out = {}
        self.role_cost_usd = {}
        for entry in u.log:
            r = entry.get("role") or "unknown"
            self.role_tokens_in[r] = self.role_tokens_in.get(r, 0) + entry["in"]
            self.role_tokens_out[r] = self.role_tokens_out.get(r, 0) + entry["out"]
            from .llm import COST_INPUT_PER_1K, COST_OUTPUT_PER_1K, COST_CACHE_READ_PER_1K
            c = (entry["in"] / 1000) * COST_INPUT_PER_1K \
              + (entry["out"] / 1000) * COST_OUTPUT_PER_1K \
              + (entry.get("cache_read", 0) / 1000) * COST_CACHE_READ_PER_1K
            self.role_cost_usd[r] = self.role_cost_usd.get(r, 0.0) + c

    # ── Layout rendering ──────────────────────────────────
    def layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="banner",   size=10),   # pyfiglet banner + ICLR footer
            Layout(name="main",     ratio=1),
            Layout(name="progress", size=5),
            Layout(name="log",      size=10),
            Layout(name="apps",     size=3),
        )
        layout["main"].split_row(
            Layout(name="role_panel", ratio=2, minimum_size=40),
            Layout(name="stats",      size=38, minimum_size=38),
        )
        return layout

    def render(self) -> Layout:
        layout = self.layout()
        layout["banner"].update(self._banner())
        layout["role_panel"].update(self._role_panel())
        layout["stats"].update(self._stats_panel())
        layout["progress"].update(self._progress_table())
        layout["log"].update(self._event_log())
        layout["apps"].update(self._apps_footer())
        return layout

    def update(self):
        if self.live is not None:
            self.live.update(self.render())

    # ── Individual renderers ───────────────────────────────────
    def _banner(self) -> Panel:
        """Pyfiglet-rendered wordmark + ICLR citation footer."""
        from rich.console import Group as RichGroup
        from rich.text import Text

        wordmark = Text(BANNER_ART, style="bold cyan")
        footer = Text(ICLR_FOOTER, style="dim italic")
        rule = Rule(style="cyan")
        body = RichGroup(Align.center(wordmark), footer)
        return Panel(
            body,
            box=box.DOUBLE,
            border_style="cyan",
            padding=(0, 1),
)

    def _role_panel(self) -> Panel:
        if not self.role:
            return Panel(
                "[dim]Initializing…[/dim]",
                title="[bold]Waiting[/bold]",
                border_style="cyan", box=box.ROUNDED,
            )
        if self.phase == "streaming":
            lines = self.content.split("\n")
            truncated = f"[dim]… [{len(lines) - 18} earlier lines] …[/dim]\n\n" \
                        if len(lines) > 18 else ""
            if self.manifest is not None and self.action == "WriteCode":
                tree = Text()
                tree.append(truncated, style="dim")
                tree.append(f"[bold]📁 {self.manifest.project_name}[/bold]\n", style="green")
                tree.append(f"  {self.manifest.summary}\n\n", style="dim")
                for f in self.manifest.files:
                    tree.append(f"  📄 [cyan]{f.path}[/cyan]")
                    if f.rationale:
                        tree.append(f"  [dim]— {f.rationale}[/dim]")
                    tree.append("\n")
                if self.manifest.dependencies:
                    tree.append(f"\n  📦 [yellow]deps:[/yellow] "
                                f"{', '.join(self.manifest.dependencies) or 'stdlib'}")
                if self.manifest.run_instructions:
                    tree.append(f"\n  ▶ [magenta]run:[/magenta] "
                                f"[dim]{self.manifest.run_instructions}[/dim]")
                body = tree
            else:
                body_text = "\n".join(lines[-18:]) if lines else ""
                body = Text(truncated + body_text)
        elif self.phase == "done":
            body = Text(self.content)
        elif self.phase == "summary":
            body = Text(self.content)
        elif self.phase == "stopped":
            body = Text(f"[red]Stopped — {self.content}[/red]")
        else:
            profile = ROLE_PROFILES.get(self.role, "")
            body = Text()
            body.append(f"[bold {self.color}]{self.role}[/bold {self.color}]", style="bold")
            body.append(f"  [dim]{profile}[/dim]\n\n")
            body.append("[dim italic]starting…[/dim italic]")

        if isinstance(body, str):
            body = Text(body)
        subtitle = (
            f"[dim]{self.tokens_in + self.tokens_out:,} tokens · "
            f"${self.cost_usd:.4f} · {self.elapsed_s:.1f}s[/dim]"
        )
        border_style = "bright_" + self.color if self.phase == "starting" else self.color
        return Panel(
            body,
            title=f"[bold {self.color}]{self.role}[/bold {self.color}] → "
                  f"[bold]{self.action}[/bold]",
            subtitle=subtitle,
            border_style=border_style, box=box.ROUNDED,
        )

    def _stats_panel(self) -> Panel:
        t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        t.add_column("Metric", style="bold")
        t.add_column("Value", justify="right")

        t.add_row("[bold]Model[/bold]", f"[cyan]{self.model}[/cyan]")
        t.add_row("[bold]Endpoint[/bold]",
                  f"[dim]{self.base_url.replace('https://', '').replace('http://', '')}[/dim]")

        ctx_pct = (self.tokens_in / self.context_window * 100) if self.context_window else 0
        ctx_str = f"{self.tokens_in:,} / {self.context_window:,} ({ctx_pct:.1f}%)"
        t.add_row("[bold]Context[/bold]", ctx_str)

        t.add_row("[bold]Tokens in[/bold]", f"{self.tokens_in:,}")
        t.add_row("[bold]Tokens out[/bold]", f"{self.tokens_out:,}")
        t.add_row("[bold]Total tokens[/bold]", f"[bold]{self.tokens_in + self.tokens_out:,}[/bold]")

        t.add_row("[bold]Cost so far[/bold]", f"[bold green]${self.cost_usd:.4f}[/bold green]")
        if self.budget_usd > 0:
            t.add_row("[bold]Budget[/bold]", f"${self.budget_usd:.2f}")

        if self.elapsed_s > 0:
            tput = (self.tokens_in + self.tokens_out) / self.elapsed_s
            t.add_row("[bold]Throughput[/bold]", f"{tput:.0f} tok/s")

        if self.role_tokens_in or self.role_tokens_out:
            t.add_row("", "")
            t.add_row("[bold]─── Per-role ───[/bold]", "")
            for r in ("ProductManager", "Architect", "Engineer", "QA"):
                rin = self.role_tokens_in.get(r, 0)
                rout = self.role_tokens_out.get(r, 0)
                rc = self.role_cost_usd.get(r, 0.0)
                if rin + rout > 0:
                    t.add_row(
                        f"  [{ROLE_COLORS.get(r, 'white')}]{r}[/{ROLE_COLORS.get(r, 'white')}]",
                        f"{rin + rout:,} tok · ${rc:.4f}",
                    )

        return Panel(t, title="[bold cyan]Mission Control[/bold cyan]",
                     border_style="cyan", box=box.ROUNDED)

    def _progress_table(self) -> Table:
        t = Table(box=box.SIMPLE, show_header=True, padding=(0, 1),
                  expand=True, header_style="bold")
        t.add_column("Role", style="bold", width=18)
        t.add_column("Action", width=14)
        t.add_column("Round", justify="center", width=6)
        t.add_column("Status", width=10)

        for rn, an, status, round_num in self.messages:
            color = ROLE_COLORS.get(rn, "white")
            if status == "active":
                sym = "[bold yellow]●[/bold yellow] active"
            elif status == "done":
                sym = "[bold green]✓[/bold green] done"
            elif status == "passed":
                sym = "[bold green]✓[/bold green] PASS"
            elif status == "failed":
                sym = "[bold red]✗[/bold red] FAIL"
            else:
                sym = "[dim]○[/dim] pending"
            t.add_row(
                f"[{color}]{rn}[/{color}]",
                an,
                str(round_num) if round_num > 0 else "—",
                sym,
            )
        return Panel(t, title="[bold cyan]Pipeline progress[/bold cyan]",
                     border_style="cyan", box=box.ROUNDED)

    def _event_log(self) -> Panel:
        body = Text()
        for e in list(self.events)[-12:]:
            ts = time.strftime("%H:%M:%S", time.localtime(e.ts))
            if e.level == "ok":
                body.append(f"[green]✓[/green] ")
            elif e.level == "warn":
                body.append(f"[yellow]![/yellow] ")
            elif e.level == "err":
                body.append(f"[red]✗[/red] ")
            else:
                body.append(f"[dim]·[/dim] ")
            body.append(f"[dim]{ts}[/dim] ")
            body.append(f"{e.msg}\n")
        return Panel(body, title="[bold cyan]Event log[/bold cyan]",
                     border_style="cyan", box=box.ROUNDED)

    def _apps_footer(self) -> Panel:
        body = Text()
        body.append("Real-world SOP-style agents: ", style="bold")
        body.append(" · ".join(REAL_WORLD_APPS), style="dim")
        return Panel(body, border_style="cyan", box=box.ROUNDED,
                     title="[dim]Used by[/dim]")


# Back-compat: render(state) used by older callers
def render(state: LiveRunState):
    return state.render()


__all__ = [
    "LiveRunState",
    "Event",
    "ROLE_COLORS",
    "ROLE_PROFILES",
    "REAL_WORLD_APPS",
    "ICLR_FOOTER",
    "BANNER_ART",
]