"""
LLM client — Anthropic Messages API, LLM-agnostic.

Supports:
  - chat()          : blocking single-turn
  - stream()        : streaming via text_stream
  - structured()    : Anthropic tool-use for guaranteed JSON output
                      (used by the Engineer for multi-file manifests)

Pricing model: $0.30/M input, $1.20/M output for MiniMax-M3.
Edit COST_INPUT_PER_1K / COST_OUTPUT_PER_1K for your provider.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Iterable, Iterator

from dotenv import load_dotenv

load_dotenv()


# ── Pricing (MiniMax-M3 standard tier, 2026) ────────────────────────────────
COST_INPUT_PER_1K = 0.00030   # $0.30 per 1M tokens
COST_OUTPUT_PER_1K = 0.00120  # $1.20 per 1M tokens
COST_CACHE_READ_PER_1K = 0.00006  # $0.06 per 1M tokens (cache hit)


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMUsage:
    """Running cost + token accounting."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    total_tokens: int = 0
    calls: int = 0
    elapsed_s: float = 0.0
    estimated_cost_usd: float = 0.0
    # Per-call log: [{ts, model, role, in, out, dt_s}]
    log: list = field(default_factory=list)

    def record(self, in_t: int, out_t: int, cache_read: int, cache_create: int,
               dt: float, model: str, role: str = ""):
        self.prompt_tokens += in_t
        self.completion_tokens += out_t
        self.cache_read_tokens += cache_read
        self.cache_creation_tokens += cache_create
        self.total_tokens += in_t + out_t + cache_read + cache_create
        self.calls += 1
        self.elapsed_s += dt
        cost = (in_t / 1000) * COST_INPUT_PER_1K \
             + (out_t / 1000) * COST_OUTPUT_PER_1K \
             + (cache_read / 1000) * COST_CACHE_READ_PER_1K
        self.estimated_cost_usd += cost
        self.log.append({
            "ts": time.time(), "model": model, "role": role,
            "in": in_t, "out": out_t,
            "cache_read": cache_read, "cache_create": cache_create,
            "dt_s": round(dt, 3),
        })


class LLM:
    """Thin Anthropic Messages API wrapper."""

    def __init__(self, model: str | None = None, base_url: str | None = None,
                 api_key: str | None = None, temperature: float | None = None,
                 max_tokens: int | None = None):
        self.model = model or os.getenv("LLM_MODEL", "MiniMax-M3")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.minimax.io/anthropic")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.temperature = temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.max_tokens = max_tokens if max_tokens is not None else int(os.getenv("LLM_MAX_TOKENS", "16384"))
        self.context_window = int(os.getenv("LLM_CONTEXT_WINDOW", "1048576"))  # MiniMax-M3: 1M
        self.usage = LLMUsage()

        if not self.api_key:
            raise RuntimeError(
                "LLM_API_KEY is not set. Add it to /Users/jkm/Projects/metagpt-mini/.env."
            )

        from anthropic import Anthropic  # type: ignore
        self._client = Anthropic(api_key=self.api_key, base_url=self.base_url)

    # ── Build kwargs from messages ────────────────────────────────
    def _build_kwargs(self, messages: list[dict], tools: list | None = None,
                      tool_choice: dict | None = None) -> dict:
        system = None
        chat_msgs = []
        for m in messages:
            if m["role"] == "system":
                system = (system or "") + m["content"] + "\n"
            else:
                chat_msgs.append(m)
        kwargs = dict(model=self.model, messages=chat_msgs,
                      max_tokens=self.max_tokens)
        if system:
            kwargs["system"] = system.strip()
        if self.temperature is not None:
            kwargs["extra_body"] = {"temperature": self.temperature}
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice
        return kwargs

    def _extract_text(self, resp) -> str:
        return "".join(
            block.text for block in resp.content
            if getattr(block, "type", "") == "text"
        )

    # ── Blocking chat ─────────────────────────────────────────────
    def chat(self, messages: Iterable[ChatMessage], *, role_tag: str = "") -> str:
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        kwargs = self._build_kwargs(msgs)
        t0 = time.perf_counter()
        resp = self._client.messages.create(**kwargs)
        dt = time.perf_counter() - t0
        usage = getattr(resp, "usage", None)
        self.usage.record(
            getattr(usage, "input_tokens", 0) or 0,
            getattr(usage, "output_tokens", 0) or 0,
            getattr(usage, "cache_read_input_tokens", 0) or 0,
            getattr(usage, "cache_creation_input_tokens", 0) or 0,
            dt, self.model, role_tag,
        )
        return self._extract_text(resp)

    # ── Streaming chat ────────────────────────────────────────────
    def stream(self, messages: Iterable[ChatMessage], *, role_tag: str = "") -> Iterator[str]:
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        kwargs = self._build_kwargs(msgs)
        t0 = time.perf_counter()
        usage = None
        with self._client.messages.stream(**kwargs) as stream:
            for text_chunk in stream.text_stream:
                yield text_chunk
            try:
                final = stream.get_final_message()
                usage = getattr(final, "usage", None)
            except Exception:
                usage = None
        dt = time.perf_counter() - t0
        self.usage.record(
            getattr(usage, "input_tokens", 0) or 0,
            getattr(usage, "output_tokens", 0) or 0,
            getattr(usage, "cache_read_input_tokens", 0) or 0,
            getattr(usage, "cache_creation_input_tokens", 0) or 0,
            dt, self.model, role_tag,
        )

    # ── Structured output via tool-use ────────────────────────────
    def structured(self, messages: Iterable[ChatMessage], *,
                   tool_name: str, tool_description: str,
                   input_schema: dict, role_tag: str = "") -> dict:
        """Force the LLM to return a JSON object matching input_schema via
        the Anthropic tool-use API. Returns the parsed dict.

        Raises json.JSONDecodeError if the model returned invalid JSON even
        after tool-use (shouldn't happen with well-formed schemas).
        """
        tool = {
            "name": tool_name,
            "description": tool_description,
            "input_schema": input_schema,
        }
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        kwargs = self._build_kwargs(
            msgs,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool_name},
        )

        t0 = time.perf_counter()
        resp = self._client.messages.create(**kwargs)
        dt = time.perf_counter() - t0
        usage = getattr(resp, "usage", None)
        self.usage.record(
            getattr(usage, "input_tokens", 0) or 0,
            getattr(usage, "output_tokens", 0) or 0,
            getattr(usage, "cache_read_input_tokens", 0) or 0,
            getattr(usage, "cache_creation_input_tokens", 0) or 0,
            dt, self.model, role_tag,
        )

        # Extract the tool use input
        for block in resp.content:
            if getattr(block, "type", "") == "tool_use":
                if block.name == tool_name:
                    return block.input
        raise RuntimeError(f"No tool_use block for {tool_name} in response")

    # ── Helpers ──────────────────────────────────────────────────
    def system_user(self, system: str, user: str, *, role_tag: str = "") -> str:
        return self.chat([
            ChatMessage("system", system),
            ChatMessage("user", user),
        ], role_tag=role_tag)


# ── Pricing utility ─────────────────────────────────────────────────────────
def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1000) * COST_INPUT_PER_1K \
         + (output_tokens / 1000) * COST_OUTPUT_PER_1K


def format_cost(usd: float) -> str:
    if usd < 0.01:
        return f"${usd * 100:.3f}¢"
    return f"${usd:.4f}"