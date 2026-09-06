"""
LLM client — provider-agnostic, talks to the Anthropic Messages API.

Works with any provider that exposes /v1/messages:
- MiniMax-M3 (https://api.minimax.io/anthropic)
- Anthropic Claude (https://api.anthropic.com)
- Any Anthropic-compatible endpoint.

Supports both blocking (.chat) and streaming (.stream) modes. The streaming
mode yields token chunks as they arrive, which is what the live UI uses.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Iterable, Iterator

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
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    total_tokens: int = 0
    calls: int = 0
    elapsed_s: float = 0.0
    estimated_cost_usd: float = 0.0
    log: list = field(default_factory=list)

    def record(self, in_t: int, out_t: int, cache_read: int, cache_create: int,
               dt: float, model: str):
        self.prompt_tokens += in_t
        self.completion_tokens += out_t
        self.cache_read_tokens += cache_read
        self.cache_creation_tokens += cache_create
        self.total_tokens += in_t + out_t + cache_read + cache_create
        self.calls += 1
        self.elapsed_s += dt
        cost_in  = (in_t / 1000) * 0.001
        cost_out = (out_t / 1000) * 0.003
        self.estimated_cost_usd += cost_in + cost_out
        self.log.append({
            "ts": time.time(),
            "model": model,
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
        self.max_tokens = max_tokens if max_tokens is not None else int(os.getenv("LLM_MAX_TOKENS", "8192"))
        self.usage = LLMUsage()

        if not self.api_key:
            raise RuntimeError(
                "LLM_API_KEY is not set. Add it to /Users/jkm/Projects/metagpt-mini/.env "
                "(copy .env.example first)."
            )

        from anthropic import Anthropic  # type: ignore
        self._client = Anthropic(api_key=self.api_key, base_url=self.base_url)

    # ── Internal: build kwargs from messages ──────────────────────
    def _build_kwargs(self, messages: list[dict]) -> dict:
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
        return kwargs

    # ── Blocking single call ─────────────────────────────────────
    def chat(self, messages: Iterable[ChatMessage], *, json_mode: bool = False) -> str:
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        kwargs = self._build_kwargs(msgs)
        t0 = time.perf_counter()
        resp = self._client.messages.create(**kwargs)
        dt = time.perf_counter() - t0
        usage = getattr(resp, "usage", None)
        in_t  = getattr(usage, "input_tokens", 0) or 0
        out_t = getattr(usage, "output_tokens", 0) or 0
        cr    = getattr(usage, "cache_read_input_tokens", 0) or 0
        cc    = getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.usage.record(in_t, out_t, cr, cc, dt, self.model)
        return "".join(
            block.text for block in resp.content
            if getattr(block, "type", "") == "text"
        )

    # ── Streaming call — yields chunks of text ────────────────────
    def stream(self, messages: Iterable[ChatMessage]) -> Iterator[str]:
        """Yield text chunks as the LLM emits them. Records usage on completion.

        Uses the Anthropic SDK's high-level text_stream iterator (which handles
        both raw and parsed event types) rather than the raw event iterator
        (which has provider-specific quirks on Anthropic-compatible endpoints
        like MiniMax)."""
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        kwargs = self._build_kwargs(msgs)

        t0 = time.perf_counter()
        usage = None
        with self._client.messages.stream(**kwargs) as stream:
            # text_stream is a clean iterator of just the text chunks
            for text_chunk in stream.text_stream:
                yield text_chunk
            try:
                final = stream.get_final_message()
                usage = getattr(final, "usage", None)
            except Exception:
                usage = None

        dt = time.perf_counter() - t0
        in_t  = getattr(usage, "input_tokens", 0) or 0
        out_t = getattr(usage, "output_tokens", 0) or 0
        cr    = getattr(usage, "cache_read_input_tokens", 0) or 0
        cc    = getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.usage.record(in_t, out_t, cr, cc, dt, self.model)

    # ── Helpers ──────────────────────────────────────────────────
    def system_user(self, system: str, user: str, *, json_mode: bool = False) -> str:
        return self.chat([
            ChatMessage("system", system),
            ChatMessage("user", user),
        ], json_mode=json_mode)