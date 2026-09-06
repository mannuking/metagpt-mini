"""
Canonical MetaGPT-Mini demo — the one you'd run in front of a class.

Builds a CLI todo app end-to-end via PM → Architect → Engineer → QA, with
MiniMax-M3 / Qwen3-8B-Flash / any other OpenAI-compatible LLM.

Usage:
    python examples/build_cli_app.py
    python examples/build_cli_app.py "Build a CLI todo app with priorities"
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

# Allow `python examples/build_cli_app.py` to find the package without install.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metagpt_mini.llm import LLM            # noqa: E402
from metagpt_mini.team import Team           # noqa: E402


def main() -> int:
    load_dotenv()

    requirement = (
        sys.argv[1] if len(sys.argv) > 1
        else "Build a CLI todo app in Python with add, list, complete, delete, "
             "and persist tasks to a JSON file. Should support priorities and "
             "due dates."
    )

    try:
        llm = LLM()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        print("Copy .env.example to .env and set LLM_API_KEY / LLM_BASE_URL / LLM_MODEL.")
        return 1

    team = Team(llm=llm, verbose=True)
    pool = team.run(requirement)

    # Save all four artifacts to disk — the canonical MetaGPT output.
    out_dir = os.path.join(os.path.dirname(__file__), "..", "output")
    os.makedirs(out_dir, exist_ok=True)

    name_map = {
        "WritePRD":    "01_prd.md",
        "WriteDesign": "02_design.md",
        "WriteCode":   "03_app.py",
        "WriteTest":   "04_test_app.py",
    }
    saved = []
    for action, filename in name_map.items():
        msgs = pool.by_action(action)
        if msgs:
            path = os.path.join(out_dir, filename)
            content = msgs[-1].content
            # Strip code fences if present for non-code files; keep raw for .py
            if filename.endswith(".py"):
                # Extract code block if wrapped in fences
                if "```python" in content:
                    content = content.split("```python", 1)[1].rsplit("```", 1)[0].strip()
                elif "```" in content:
                    content = content.split("```", 1)[1].rsplit("```", 1)[0].strip()
            with open(path, "w") as f:
                f.write(content)
            saved.append(path)

    print("\nArtifacts saved:")
    for p in saved:
        print(f"  {p}")
    print(f"\nNext: cd output && python 03_app.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())