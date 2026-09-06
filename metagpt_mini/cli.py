"""CLI entry points — single command runs everything via `uv run metagpt ...`.

After install (or just `uv run metagpt ...` from a fresh clone), you get:
  uv run metagpt                 # run the canonical demo (CLI todo app)
  uv run metagpt "your prompt"   # run the demo with your own requirement
  uv run metagpt test            # run unit tests
  uv run metagpt ping            # single LLM ping (prove the API key works)
  uv run metagpt pdf             # regenerate the learning PDF

No `source .venv`, no pip install, no manual activation. uv handles everything.
"""

import os
import subprocess
import sys
from pathlib import Path


def _load_env() -> None:
    """Load .env from the project root if present (no-op if missing)."""
    try:
        from dotenv import load_dotenv
        root = Path(__file__).resolve().parent.parent
        load_dotenv(root / ".env")
    except ImportError:
        pass  # dotenv missing — uv will install it on first run


def main() -> int:
    """Entry point for the `metagpt` console script."""
    _load_env()

    # Parse args: first arg = subcommand OR requirement, default = demo
    if len(sys.argv) == 1:
        # No args → run the canonical demo (live UI mode)
        return _run_demo(live=True)

    # Check for --plain flag
    args = sys.argv[1:]
    live = True
    if "--plain" in args:
        live = False
        args = [a for a in args if a != "--plain"]

    if not args:
        return _run_demo(live=live)

    cmd = args[0]
    rest = args[1:]

    if cmd in ("test", "tests"):
        return test_cmd()
    if cmd == "ping":
        return ping_cmd()
    if cmd == "pdf":
        return _rebuild_pdf()
    if cmd in ("-h", "--help", "help"):
        _print_help()
        return 0

    # Otherwise treat all args as a custom requirement
    requirement = " ".join(args)
    return _run_demo(requirement, live=live)


def test_cmd() -> int:
    """Run pytest with verbose output."""
    print("Running unit tests ...")
    return subprocess.call([sys.executable, "-m", "pytest", "tests/", "-v"])


def ping_cmd() -> int:
    """Single LLM ping — proves the API key + URL combo works."""
    _load_env()
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from metagpt_mini.llm import LLM, ChatMessage

    if not os.getenv("LLM_API_KEY"):
        print("ERROR: LLM_API_KEY not set. Add it to /Users/jkm/Projects/metagpt-mini/.env")
        print("  LLM_API_KEY=sk-your-key-here")
        print("  LLM_BASE_URL=https://api.minimax.io/anthropic")
        print("  LLM_MODEL=MiniMax-M3")
        return 1

    try:
        llm = LLM()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return 1

    resp = llm.chat([
        ChatMessage("user", "Reply with exactly one word: pong"),
    ])
    print(f"Response: {resp!r}")
    print(f"Usage: {llm.usage.calls} call, {llm.usage.total_tokens} tokens, "
          f"est. cost ${llm.usage.estimated_cost_usd:.4f}")
    return 0


def _strip_code_fences(content: str) -> str:
    """Strip ```python ... ``` fences from LLM output.

    Handles all variants:
    - ```python ... ```  (standard)
    - ``` ... ```        (no language tag)
    - ```python ...      (truncated — no closing fence; we keep everything after opener)
    - plain code (no fences at all)
    """
    content = content.strip()

    # Find the opening fence
    open_pos = -1
    open_len = 0
    for marker in ("```python\n", "```python\r\n", "```\n", "```\r\n", "```python", "```"):
        idx = content.find(marker)
        if idx != -1:
            open_pos = idx + len(marker)
            open_len = len(marker)
            break

    if open_pos == -1:
        # No opening fence — return as-is
        return content

    # Find the LAST closing fence (after open_pos)
    close_pos = content.rfind("```")
    if close_pos > open_pos:
        return content[open_pos:close_pos].strip()

    # No closing fence (truncated output) — take everything after the opener,
    # then strip any trailing partial line if the output cut mid-token.
    body = content[open_pos:].rstrip()
    # If body ends mid-line (no terminating newline + looks like a partial token),
    # trim back to the last complete line to avoid syntax errors.
    if body and not body.endswith(("\n", "```")):
        last_nl = body.rfind("\n")
        if last_nl != -1:
            body = body[:last_nl]
    return body.strip()


def _run_demo(requirement: str | None = None, *, live: bool = True) -> int:
    """Run the canonical MetaGPT-Mini demo.

    live=True  → beautiful real-time UI (class demo default)
    live=False → blocking panel-by-panel output (for piping/scripting)
    """
    _load_env()
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    if not os.getenv("LLM_API_KEY"):
        print("ERROR: LLM_API_KEY not set. Add it to /Users/jkm/Projects/metagpt-mini/.env")
        print("  LLM_API_KEY=sk-your-key-here")
        print("  LLM_BASE_URL=https://api.minimax.io/anthropic")
        print("  LLM_MODEL=MiniMax-M3")
        return 1

    from metagpt_mini.llm import LLM
    from metagpt_mini.team import Team

    if requirement is None:
        requirement = (
            "Build a CLI todo app in Python with add, list, complete, delete, "
            "and persist tasks to a JSON file. Should support priorities and "
            "due dates."
        )

    try:
        llm = LLM()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return 1

    team = Team(llm=llm, verbose=not live, live=live)
    pool = team.run(requirement)

    # Save artifacts
    out_dir = Path(__file__).resolve().parent.parent / "output"
    out_dir.mkdir(exist_ok=True)
    saved = []
    for action, fname in [
        ("WritePRD",    "01_prd.md"),
        ("WriteDesign", "02_design.md"),
        ("WriteCode",   "03_app.py"),
        ("WriteTest",   "04_test_app.py"),
    ]:
        msgs = pool.by_action(action)
        if msgs:
            content = msgs[-1].content
            if fname.endswith(".py"):
                content = _strip_code_fences(content)
            path = out_dir / fname
            path.write_text(content)
            saved.append(str(path))

    if saved:
        print()
        print("Artifacts saved:")
        for p in saved:
            print(f"  {p}")
        print()
        print("Next: cd output && python 03_app.py --help")
    return 0


def _rebuild_pdf() -> int:
    """Regenerate the learning guide PDF."""
    root = Path(__file__).resolve().parent.parent
    script = root / "docs" / "build_pdf.py"
    if not script.exists():
        print(f"ERROR: {script} not found")
        return 1
    print(f"Rebuilding PDF via {script} ...")
    return subprocess.call([sys.executable, str(script)])


def _print_help() -> None:
    print("MetaGPT-Mini — uv-managed, single-command orchestrator")
    print()
    print("Usage:")
    print("  uv run metagpt                 Run the canonical demo with live UI")
    print("  uv run metagpt --plain          Run the canonical demo, blocking output")
    print("  uv run metagpt \"<requirement>\"  Run the demo on your own requirement")
    print("  uv run metagpt test            Run unit tests (3 schema tests)")
    print("  uv run metagpt ping            Single LLM ping (proves API key works)")
    print("  uv run metagpt pdf             Regenerate the learning guide PDF")
    print("  uv run metagpt help            Show this help")
    print()
    print("The live UI shows: token-by-token streaming, per-role banners,")
    print("live token + cost counters, and a final summary panel.")
    print()
    print("Environment:")
    print("  All configuration is in .env (copy from .env.example). Required:")
    print("    LLM_API_KEY    — your provider key")
    print("    LLM_BASE_URL   — Anthropic-compatible endpoint")
    print("    LLM_MODEL      — model name")


if __name__ == "__main__":
    raise SystemExit(main())