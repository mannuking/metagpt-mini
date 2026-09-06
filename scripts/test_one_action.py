"""Single-action test — runs ONLY the ProductManager's WritePRD action.

Use this to prove the LLM responds well to MetaGPT-style system prompts
before running the full 4-role demo. Faster feedback loop.
"""

import os, sys
sys.path.insert(0, "/Users/jkm/Projects/metagpt-mini")

from dotenv import load_dotenv
load_dotenv("/Users/jkm/Projects/metagpt-mini/.env")

if not os.getenv("LLM_API_KEY"):
    print("Set LLM_API_KEY in /Users/jkm/Projects/metagpt-mini/.env first.")
    sys.exit(1)

from metagpt_mini.llm import LLM
from metagpt_mini.actions import WritePRD
from metagpt_mini.schema import MessagePool

llm = LLM()
pool = MessagePool()

print(f"Model: {llm.model}")
print(f"URL:   {llm.base_url}")
print(f"Temp:  {llm.temperature}")
print()
print("Running WritePRD only ...")
print("=" * 70)

prd_msg = WritePRD(llm).run(
    requirement="Build a CLI todo app in Python with add, list, complete, "
                "delete, priorities, due dates, and JSON persistence.",
    pool=pool,
)
print(prd_msg.content)
print()
print("=" * 70)
print(f"Cost: ${llm.usage.estimated_cost_usd:.4f}  "
      f"Tokens: {llm.usage.total_tokens}  "
      f"Calls: {llm.usage.calls}")
print(f"Pool now has {len(pool.messages)} message(s).")