"""
LLM client — provider-agnostic via OpenAI Chat Completions API.

Works with any provider that exposes the OpenAI-compatible endpoint:
- MiniMax-M3
- Qwen3-8B-Flash
- Local Ollama / LM Studio
- (you can swap, no code change required)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Iterable

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMUsage:
    """Running cost / token accounting across the run."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    calls: int = 0
    elapsed_s: float = 0.0
    estimated_cost_usd: float = 0.0
    log: list = field(default_factory=list)

    def record(self, prompt_tokens: int, completion_tokens: int, dt: float, model: str):
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        self.calls += 1
        self.elapsed_s += dt
        # Conservative USD estimate; user can override in cost_per_1k
        # Defaults: $0.15/1k in, $0.60/1k out — typical 7-8B cloud tier.
        cost_in = (prompt_tokens / 1000) * 0.15
        cost_out = (completion_tokens / 1000) * 0.60
        self.estimated_cost_usd += cost_in + cost_out
        self.log.append({
            "ts": time.time(),
            "model": model,
            "in": prompt_tokens,
            "out": completion_tokens,
            "dt_s": round(dt, 3),
        })


class LLM:
    """Thin OpenAI-compatible wrapper. Stateless across calls."""

    def __init__(self, model: str | None = None, base_url: str | None = None,
                 api_key: str | None = None, temperature: float | None = None,
                 max_tokens: int | None = None):
        self.model = model or os.getenv("LLM_MODEL", "MiniMax-M3")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.minimax.chat/v1")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.temperature = temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.max_tokens = max_tokens if max_tokens is not None else int(os.getenv("LLM_MAX_TOKENS", "2048"))
        self.usage = LLMUsage()

        if not self.api_key:
            raise RuntimeError(
                "LLM_API_KEY is not set. Copy .env.example to .env and set your key."
            )

        # Lazy import so the package can be imported for schema tests without openai installed.
        from openai import OpenAI  # type: ignore
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    # ── Single-turn chat ─────────────────────────────────────────
    def chat(self, messages: Iterable[ChatMessage], *, json_mode: bool = False) -> str:
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        kwargs = dict(model=self.model, messages=msgs,
                      temperature=self.temperature, max_tokens=self.max_tokens)
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        t0 = time.perf_counter()
        resp = self._client.chat.completions.create(**kwargs)
        dt = time.perf_counter() - t0
        usage = getattr(resp, "usage", None)
        pt = getattr(usage, "prompt_tokens", 0) or 0
        ct = getattr(usage, "completion_tokens", 0) or 0
        self.usage.record(pt, ct, dt, self.model)
        return resp.choices[0].message.content or ""

    # ── Helpers ──────────────────────────────────────────────────
    def system_user(self, system: str, user: str, *, json_mode: bool = False) -> str:
        return self.chat([
            ChatMessage("system", system),
            ChatMessage("user", user),
        ], json_mode=json_mode)