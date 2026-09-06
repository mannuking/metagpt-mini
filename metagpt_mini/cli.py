"""
CLI entry points for MetaGPT-Mini.

Commands:
  uv run metagpt                   Blocking demo (rich panel output, full artifacts)
  uv run metagpt --live            Full-screen live TUI (the class demo!)
  uv run metagpt init              Alias for --live
  uv run metagpt "<requirement>"   Custom requirement (blocking)
  uv run metagpt --live "<req>"    Custom requirement (live TUI)
  uv run metagpt test              Run unit tests
  uv run metagpt ping              Single LLM ping
  uv run metagpt pdf               Regenerate learning PDF
  uv run metagpt help              Show help

No `source .venv`, no pip — uv handles everything.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        root = Path(__file__).resolve().parent.parent
        load_dotenv(root / ".env")
    except ImportError:
        pass


def _detect_python_cmd() -> str:
    """Detect the right Python command for the user's shell (zsh on Mac, bash elsewhere)."""
    shell = os.environ.get("SHELL", "")
    is_zsh = "zsh" in shell
    # On Mac, `python` is often missing; `python3` always works.
    # On Linux, both usually work; `python3` is safer.
    for cmd in ("python3", "python"):
        try:
            r = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=2)
            if r.returncode == 0:
                return cmd
        except Exception:
            continue
    return "python3"  # fallback


def _detect_activate_cmd() -> str:
    """uv handles env activation; users just need 'uv run metagpt'."""
    return ""


def _comment_style_for(path: str) -> tuple[str, str]:
    """Return (prefix, comment_style) for a file path.
    prefix is the line-comment marker, or '' for files with no line-comment style.
    Used so we can stamp a banner header that's actually valid syntax.
    """
    ext = Path(path).suffix.lower()
    return {
        ".py": "#",
        ".sh": "#",
        ".yaml": "#",
        ".yml": "#",
        ".toml": "#",
        ".cfg": "#",
        ".ini": "#",
        ".rb": "#",
        ".pl": "#",
        ".md": "<!--",
        ".html": "<!--",
        ".css": "/*",
        ".js": "//",
        ".ts": "//",
        ".go": "//",
        ".rs": "//",
        ".c": "//",
        ".cpp": "//",
        ".h": "//",
        ".java": "//",
        ".sh": "#",
    }.get(ext, "#")  # default: #


def _strip_code_fences(content: str) -> str:
    """Strip ```python ... ``` fences that LLMs often wrap code in.
    Handles: standard fences, missing language tag, no closing fence (truncation),
    no fences at all, indented blocks, leading/trailing whitespace.
    """
    if not content:
        return content

    lines = content.split("\n")
    n = len(lines)

    # Find first opening fence line (any line starting with ```)
    first_fence = -1
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            first_fence = i
            break

    if first_fence == -1:
        # No fences at all
        return content.rstrip() + "\n"

    # Find last closing fence line (search from end)
    last_fence = -1
    for i in range(n - 1, first_fence - 1, -1):
        if lines[i].lstrip().startswith("```"):
            last_fence = i
            break

    # Extract content between fences (exclusive of the fence lines)
    if last_fence == -1 or last_fence == first_fence:
        # Truncated: only an opening fence, no closing. Keep content after the
        # opening fence line (sometimes the LLM writes code right after).
        body_lines = lines[first_fence + 1:]
    elif last_fence > first_fence:
        # Both fences present. Keep content between them.
        body_lines = lines[first_fence + 1:last_fence]
    else:
        # Shouldn't happen (last_fence would be -1 caught above)
        body_lines = lines

    # If there's no body, return the original (best effort)
    if not any(l.strip() for l in body_lines):
        return content.rstrip() + "\n"

    return "\n".join(body_lines).rstrip() + "\n"


def _make_artifact_header(filename: str, requirement: str, run_id: str,
                          model: str) -> str:
    """The header comment prepended to every saved file.
    Picks the right comment style for the file extension so it's valid syntax.
    For Markdown/HTML, wraps in <!-- ... -->. For CSS, /* ... */. For everything
    else, uses # (works as a Python comment, a shell comment, a TOML comment, etc.)
    """
    today = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    style = _comment_style_for(filename)
    lines = [
        "─" * 65,
        f"File:        {filename}",
        f"Project:     MetaGPT-Mini generated project",
        f"Run id:      {run_id}",
        f"Requirement: {requirement[:80]}{'…' if len(requirement) > 80 else ''}",
        f"Model:       {model}",
        f"Generated:   {today}",
        f"SOP:         ProductManager → Architect → Engineer → QA",
        f"Paper:       MetaGPT (ICLR 2024 Oral, top 1.2%, #1 LLM-Agent)",
        f"Reimpl:      https://github.com/mannuking/metagpt-mini",
        "─" * 65,
    ]
    if style == "<!--":
        return "<!--\n" + "\n".join(lines) + "\n-->\n\n"
    if style == "/*":
        return "/*\n" + "\n".join(lines) + "\n*/\n\n"
    return style + " " + ("\n" + style + " ").join(lines) + "\n\n"


def main() -> int:
    """Entry point for the `metagpt` console script."""
    _load_env()
    args = sys.argv[1:]

    # Parse --live / --plain flags
    live = False
    if "--live" in args:
        live = True
        args = [a for a in args if a != "--live"]
    if "--plain" in args:
        live = False
        args = [a for a in args if a != "--plain"]

    # No args → default to full-screen live TUI (the class demo!)
    if not args:
        return _run_demo(live=True)

    cmd = args[0]
    rest = args[1:]

    if cmd == "init":
        # Explicit full-screen live TUI (alias for the default)
        if not rest:
            req = (
                "Build a Python CLI todo app with add, list, complete, delete, "
                "priorities, due dates, and JSON persistence."
            )
        else:
            req = " ".join(rest)
        return _run_demo(req, live=True)

    if cmd in ("test", "tests"):
        return test_cmd()
    if cmd == "ping":
        return ping_cmd()
    if cmd == "pdf":
        return _rebuild_pdf()
    if cmd in ("-h", "--help", "help"):
        _print_help()
        return 0

    # Otherwise treat as a requirement
    requirement = " ".join(args)
    return _run_demo(requirement, live=live)


def test_cmd() -> int:
    print("Running unit tests ...")
    return subprocess.call([sys.executable, "-m", "pytest", "tests/", "-v"])


def ping_cmd() -> int:
    _load_env()
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from metagpt_mini.llm import LLM, ChatMessage

    if not os.getenv("LLM_API_KEY"):
        print("ERROR: LLM_API_KEY not set. Add it to .env.")
        return 1
    try:
        llm = LLM()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return 1

    resp = llm.chat([ChatMessage("user", "Reply with exactly one word: pong")],
                    role_tag="ping")
    print(f"Response: {resp!r}")
    print(f"Usage: {llm.usage.calls} call, {llm.usage.total_tokens} tokens, "
          f"est. cost ${llm.usage.estimated_cost_usd:.4f}")
    return 0


def _run_demo(requirement: str | None = None, *, live: bool = False) -> int:
    """Run the canonical MetaGPT-Mini demo."""
    _load_env()
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    if not os.getenv("LLM_API_KEY"):
        print("ERROR: LLM_API_KEY not set. Add it to /Users/jkm/Projects/metagpt-mini/.env")
        print("  LLM_API_KEY=sk-your-key-here")
        print("  LLM_BASE_URL=https://api.minimax.io/anthropic")
        print("  LLM_MODEL=MiniMax-M3")
        return 1

    from metagpt_mini.llm import LLM
    from metagpt_mini.team import Team, RunResult
    from metagpt_mini.schema import new_run_id

    if requirement is None:
        requirement = (
            "Build a Python CLI todo app with add, list, complete, delete, "
            "priorities, due dates, and JSON persistence."
        )

    run_id = new_run_id(requirement)
    print(f"[metagpt-mini] run_id = {run_id}")
    print(f"[metagpt-mini] requirement = {requirement}")
    print()

    try:
        llm = LLM()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return 1

    team = Team(llm=llm, live=live)
    result: RunResult = team.run(requirement)

    # Save artifacts
    saved, test_result = _save_artifacts(result, run_id, requirement, llm.model)

    # Print next-step hints (shell-aware)
    _print_next_steps(saved, run_id, requirement, llm, test_result, live)

    return 0 if result.qa_passed or result.manifest else 1


def _save_artifacts(result, run_id, requirement, model):
    """Write manifest files to disk with banner comments."""
    out_dir = Path(__file__).resolve().parent.parent / "output"
    out_dir.mkdir(exist_ok=True)

    saved = []
    test_result = None

    # Save the PRD
    prd = result.pool.latest_of("WritePRD")
    if prd:
        path = out_dir / "01_prd.md"
        header = _make_artifact_header("01_prd.md", requirement, run_id, model)
        # Mark down header
        md_header = f"# PRD · run {run_id}\n\n"
        path.write_text(md_header + header.replace("//", "#") + prd.content)
        saved.append(str(path))

    # Save the design
    design = result.pool.latest_of("WriteDesign")
    if design:
        path = out_dir / "02_design.md"
        md_header = f"# Design · run {run_id}\n\n"
        path.write_text(md_header + header.replace("//", "#") + design.content)
        saved.append(str(path))

    # Save the multi-file project (from the manifest)
    manifest = result.manifest
    if manifest:
        project_dir = out_dir / manifest.project_name
        project_dir.mkdir(exist_ok=True)
        # Top-level README
        # If the engineer already included a README.md in the manifest,
        # skip our auto-generated one — otherwise overwrite it.
        has_engineer_readme = any(f.path.lower() == "readme.md" for f in manifest.files)
        if not has_engineer_readme:
            readme_path = project_dir / "README.md"
            readme_content = (
                f"# {manifest.project_name}\n\n"
                f"{manifest.summary}\n\n"
                f"Generated by MetaGPT-Mini · run `{run_id}` · model `{model}`\n\n"
                f"## Run\n\n```bash\n{manifest.run_instructions}\n```\n\n"
                f"## Files\n\n" +
                "\n".join(f"- `{f.path}` — {f.rationale}" for f in manifest.files) +
                (f"\n\n## Dependencies\n\n{', '.join(manifest.dependencies)}\n"
                 if manifest.dependencies else "")
            )
            readme_path.write_text(readme_content)
            saved.append(str(readme_path))

        for f in manifest.files:
            full = project_dir / f.path
            full.parent.mkdir(parents=True, exist_ok=True)
            ext = full.suffix.lower()
            # Strip any ```python ... ``` fences the LLM wrapped the code in
            clean_content = _strip_code_fences(f.content)
            header = _make_artifact_header(f.path, requirement, run_id, model)
            if ext in (".py", ".sh", ".yaml", ".yml", ".toml", ".cfg", ""):
                content = header + clean_content
            elif ext in (".md", ".txt"):
                content = f"# {f.path} · run {run_id}\n\n" + clean_content
            else:
                content = clean_content
            full.write_text(content)
            saved.append(str(full))

        # Run pytest on the generated test files (auto-test)
        test_files = [str(p) for p in (project_dir).rglob("test_*.py")]
        if test_files:
            print(f"\n[auto-test] running pytest on {len(test_files)} generated test file(s)…")
            test_result = subprocess.run(
                [sys.executable, "-m", "pytest"] + test_files + ["-q", "--tb=line"],
                capture_output=True, text=True,
            )
            print(test_result.stdout[-1000:])
            if test_result.returncode != 0:
                print(test_result.stderr[-500:])

    # Save the QA report
    qa = result.pool.latest_of("WriteTest")
    if qa:
        path = out_dir / "03_qa_report.md"
        qa_header = f"# QA Report · run {run_id} · verdict={'PASS' if result.qa_passed else 'FAIL'}\n\n"
        path.write_text(qa_header + qa.content)
        saved.append(str(path))

    # Save run summary
    summary_path = out_dir / "04_run_summary.json"
    summary = {
        "run_id": run_id,
        "requirement": requirement,
        "model": model,
        "qa_passed": result.qa_passed,
        "qa_rounds": result.qa_rounds,
        "aborted_reason": result.aborted_reason,
        "tokens_in": result.pool and len(result.pool.messages),  # placeholder
        "cost_usd": 0.0,  # filled in by caller
        "files_generated": [f.path for f in (manifest.files if manifest else [])],
    }
    summary_path.write_text("{\n  \"see\": \"01_prd.md, 02_design.md, "
                            f"{manifest.project_name if manifest else 'NONE'}/\"\n}}")
    saved.append(str(summary_path))

    return saved, test_result


def _print_next_steps(saved, run_id, requirement, llm, test_result, live):
    py = _detect_python_cmd()
    print()
    print("═" * 72)
    print(f"[metagpt-mini] ✓ Run {run_id} complete")
    u = llm.usage
    print(f"  calls: {u.calls}  ·  tokens: {u.total_tokens:,} "
          f"(in {u.prompt_tokens:,} / out {u.completion_tokens:,})")
    print(f"  elapsed: {u.elapsed_s:.1f}s  ·  cost: ${u.estimated_cost_usd:.4f}")
    if test_result is not None:
        if test_result.returncode == 0:
            print(f"  pytest:   [green]✓ passed[/green]")
        else:
            print(f"  pytest:   [red]✗ failed[/red] (see output above)")
    print()
    print("Artifacts written:")
    for s in saved:
        print(f"  → {s}")
    print()
    # Find the generated project dir for run instructions
    out_dir = Path(__file__).resolve().parent.parent / "output"
    subdirs = [d for d in out_dir.iterdir() if d.is_dir()] if out_dir.exists() else []
    if subdirs:
        proj = subdirs[-1]
        print("Next steps (run on Mac/Linux):")
        print(f"  cd output/{proj.name}")
        if (proj / "src").exists():
            main_py = next((proj / "src").rglob("main.py"), None) or next((proj / "src").rglob("__main__.py"), None)
            if main_py:
                rel = main_py.relative_to(proj)
                print(f"  {py} -m {str(rel).replace('/', '.').replace('.py', '')}")
        elif (proj / "main.py").exists():
            print(f"  {py} main.py")
        elif (proj / "app.py").exists():
            print(f"  {py} app.py")
        print(f"  {py} -m pytest -v     # run the generated tests")
    print()
    if live:
        print("[Note] You used --live (full-screen TUI). Next time, try `uv run metagpt`")
        print("       (blocking) for quick runs and `--live` for the class demo.")
    print()
    print(f"Full run details: cat output/01_prd.md  output/02_design.md  "
          f"output/03_qa_report.md")


def _rebuild_pdf() -> int:
    root = Path(__file__).resolve().parent.parent
    script = root / "docs" / "build_pdf.py"
    if not script.exists():
        print(f"ERROR: {script} not found")
        return 1
    print(f"Rebuilding PDF via {script} …")
    return subprocess.call([sys.executable, str(script)])


def _print_help() -> None:
    print("MetaGPT-Mini — LLM-agnostic reimplementation of MetaGPT (ICLR 2024 Oral)")
    print()
    print("Usage:")
    print("  uv run metagpt                    Full-screen live TUI (default — the show!)")
    print("  uv run metagpt --plain            Blocking demo with rich panels")
    print("  uv run metagpt init               Full-screen TUI (alias for default)")
    print("  uv run metagpt init \"<req>\"       Full-screen TUI with custom requirement")
    print("  uv run metagpt \"<requirement>\"     Full-screen TUI with custom requirement")
    print("  uv run metagpt test               Run unit tests (6 schema tests)")
    print("  uv run metagpt ping               Single LLM ping (proves API key)")
    print("  uv run metagpt pdf                Regenerate the learning guide PDF")
    print("  uv run metagpt help               Show this help")
    print()
    print("The live TUI shows: pyfiglet banner, per-role streaming panels,")
    print("live token + cost counters, progress table, event log, real-world apps footer.")
    print()
    print("Pro tip: Maximize your terminal before running — the TUI uses the full screen.")
    print()
    print("Two-command workflow:")
    print("  1. uv sync       (cold start: install deps + create venv)")
    print("  2. uv run metagpt  (opens the full-screen TUI demo)")
    print()
    print("LLM-agnostic. Defaults to MiniMax-M3 via Anthropic-compat API.")
    print("Edit .env to switch provider. Pricing: $0.30/M in, $1.20/M out (MiniMax-M3).")


if __name__ == "__main__":
    raise SystemExit(main())