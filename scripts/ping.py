"""Live LLM ping — proves the MiniMax-M3 key + URL combo works."""
import os, sys
sys.path.insert(0, "/Users/jkm/Projects/metagpt-mini")

# Load .env if it exists
try:
    from dotenv import load_dotenv
    load_dotenv("/Users/jkm/Projects/metagpt-mini/.env")
except Exception as e:
    print(f"Note: dotenv load skipped: {e}")

# Show what we have
print(f"LLM_API_KEY set: {bool(os.getenv('LLM_API_KEY'))} (len={len(os.getenv('LLM_API_KEY', ''))})")
print(f"LLM_BASE_URL: {os.getenv('LLM_BASE_URL')}")
print(f"LLM_MODEL: {os.getenv('LLM_MODEL')}")

if not os.getenv("LLM_API_KEY"):
    print("\nNo LLM_API_KEY in env. Set it first:")
    print("  export LLM_API_KEY='sk-your-key-here'")
    print("  python scripts/ping.py")
    sys.exit(1)

from metagpt_mini.llm import LLM, ChatMessage

llm = LLM()
resp = llm.chat([
    ChatMessage("user", "Reply with exactly one word: pong"),
])
print(f"\nResponse: {resp!r}")
print(f"Usage: {llm.usage.calls} call, {llm.usage.total_tokens} tokens, "
      f"est. cost ${llm.usage.estimated_cost_usd:.4f}")