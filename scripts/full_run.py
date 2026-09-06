"""Full 4-role demo with detailed timing.

Runs the complete SOP (PM -> Architect -> Engineer -> QA) on a small
requirement and prints per-role stats. Use this for the actual class demo.
"""

import os, sys, time
sys.path.insert(0, "/Users/jkm/Projects/metagpt-mini")

from dotenv import load_dotenv
load_dotenv("/Users/jkm/Projects/metagpt-mini/.env")

if not os.getenv("LLM_API_KEY"):
    print("Set LLM_API_KEY in /Users/jkm/Projects/metagpt-mini/.env first.")
    sys.exit(1)

from metagpt_mini.llm import LLM
from metagpt_mini.team import Team
from metagpt_mini.schema import MessagePool

llm = LLM()
team = Team(llm=llm, verbose=False)  # we'll print our own stats

# A small requirement — fast for the live demo
requirement = (
    "Build a Python CLI calculator that supports +, -, *, /, and "
    "keeps a history of the last 10 calculations."
)

t0 = time.perf_counter()
pool = team.run(requirement)
elapsed = time.perf_counter() - t0

print()
print("=" * 70)
print(f"Total wall time: {elapsed:.1f}s")
print(f"LLM calls:       {llm.usage.calls}")
print(f"Total tokens:    {llm.usage.total_tokens:,} "
      f"(in {llm.usage.prompt_tokens:,} / out {llm.usage.completion_tokens:,})")
print(f"Estimated cost:  ${llm.usage.estimated_cost_usd:.4f}")
print()
print("Message trace:")
for i, m in enumerate(pool.history(), 1):
    print(f"  {i}. [{m.role}] {m.cause_by}  ({len(m.content)} chars)")

# Save artifacts
out_dir = "/Users/jkm/Projects/metagpt-mini/output"
os.makedirs(out_dir, exist_ok=True)
for action, fname in [
    ("WritePRD",    "01_prd.md"),
    ("WriteDesign", "02_design.md"),
    ("WriteCode",   "03_app.py"),
    ("WriteTest",   "04_test_app.py"),
]:
    msgs = pool.by_action(action)
    if msgs:
        content = msgs[-1].content
        if fname.endswith(".py") and "```" in content:
            # Strip code fences
            for fence in ["```python", "```"]:
                if fence in content:
                    parts = content.split(fence)
                    if len(parts) >= 3:
                        content = parts[1]
                        break
        path = os.path.join(out_dir, fname)
        with open(path, "w") as f:
            f.write(content)
        print(f"  Saved {path} ({len(content)} chars)")

print()
print("Next: cd /Users/jkm/Projects/metagpt-mini/output")
print("      python 03_app.py --help")
print("      pytest 04_test_app.py -v")