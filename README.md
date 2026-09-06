# MetaGPT-Mini

A clean, from-scratch reimplementation of **MetaGPT** (Hong et al., **ICLR 2024 Oral**, top 1.2%, ranked **#1** in the LLM-Agent category) with a **live animated UI** for the class demo.

This is not a wrapper around the original `geekan/MetaGPT`. It is a re-engineered, transparent implementation you can read, modify, and demo live in front of a class.

## What MetaGPT actually does (and what we re-implement)

MetaGPT encodes **Standard Operating Procedures (SOPs)** from human software teams into prompt sequences. Instead of one mega-agent, you get a **society of role-specialised agents** that collaborate via a shared message pool:

```
User → ProductManager → Architect → Engineer → QA → Code
```

Each agent:
- reads from a shared `MessagePool`
- emits structured `Message` objects with `role`, `content`, and `cause_by`
- only listens to messages from roles it depends on

## The class demo — beautiful, animated, real-time

When you run `uv run metagpt`, you get:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║    __  __          _ _      _____         _                                  ║
║   |  \/  | ___  __| (_) ___|  __ \___  __| |_   _ _ __ ___                   ║
║   | |\/| |/ _ \/ _` | |/ _ \  |__) / _ \/ _` | | | | '_ ` _ \                ║
║   | |  | |  __/ (_| | |  __/  ___/  __/ (_| | |_| | | | | | |                ║
╚══════════════════════════════════════════════════════════════════════════════╝
╭───────── ProductManager -> WritePRD ─────────╮╭─────────── Stats ────────────╮
│ ProductManager is drafting PRD...             ││    Tokens in          254    │
│                                              ││    Tokens out       1,213    │
╰──────── 1,467 tokens  ·  $0.0039 ────────────╯╰──────────────────────────────╯

   ProductManager     WritePRD        ● active
   Architect          WriteDesign     ○ pending
   Engineer           WriteCode       ○ pending
   QA                 WriteTest       ○ pending
────────────────────────────────────────────────────────────────────────────────
```

- ASCII logo banner
- Per-role panel that streams tokens in real time as the LLM emits them
- Live token + cost counter (right column)
- Per-role progress table (pending → active → done)

## The two-command workflow

```bash
# 1. Sync deps + create .venv (cold start, only needed once or after pyproject changes)
uv sync

# 2. Run the live demo with animated UI (no source, no manual activate)
uv run metagpt
```

That's it. `uv` handles everything: venv, deps, package install, console-script invocation.

## What you get

After `uv run metagpt` completes, you have a fully-implemented CLI app + tests in `output/`:

```
output/
├── 01_prd.md         # ProductManager's PRD
├── 02_design.md      # Architect's design doc
├── 03_app.py         # Engineer's runnable Python module
└── 04_test_app.py    # QA's pytest module
```

## Other commands

```bash
uv run metagpt                 # Canonical demo with live UI (default)
uv run metagpt --plain          # Canonical demo with blocking output (for piping)
uv run metagpt "your req"      # Run on your own requirement
uv run metagpt test            # Run unit tests (3 schema tests)
uv run metagpt ping            # Single LLM ping (proves API key works)
uv run metagpt pdf             # Regenerate the learning guide PDF
uv run metagpt help            # Show all options
```

## LLM-agnostic by design›

The framework talks to the Anthropic Messages API. Any provider that exposes `/v1/messages` works:

| Provider | `LLM_BASE_URL` | `LLM_MODEL` example |
|----------|----------------|----------------------|
| **MiniMax-M3** | `https://api.minimax.io/anthropic` | `MiniMax-M3` |
| **Anthropic Claude** | `https://api.anthropic.com` | `claude-3-5-sonnet-latest` |
| Local Ollama (Anthropic-compat) | `http://localhost:11434` | `qwen2.5-coder:7b` |

## Project layout

```
metagpt-mini/
├── README.md
├── pyproject.toml            # uv-managed, single source of truth
├── uv.lock                   # frozen deps (committed for reproducibility)
├── .env.example
├── metagpt_mini/
│   ├── __init__.py
│   ├── llm.py                # Anthropic Messages client (chat + stream)
│   ├── schema.py             # Message, MessagePool
│   ├── actions.py            # WritePRD, WriteDesign, WriteCode, WriteTest
│   ├── roles.py              # ProductManager, Architect, Engineer, QA
│   ├── team.py               # orchestrator + budget guard
│   ├── ui.py                 # Live animated UI (rich-live)
│   └── cli.py                # `metagpt` console script
├── examples/
│   └── build_cli_app.py      # blocking-mode demo (use `uv run metagpt` instead)
├── scripts/
│   ├── ping.py               # single LLM ping
│   ├── test_one_action.py    # single-role test
│   └── full_run.py           # full demo with timing
├── tests/
│   └── test_schema.py        # 3 unit tests
└── docs/
    ├── build_pdf.py
    └── MetaGPT-Mini-Learning-Guide.pdf
```

## Reference

```bibtex
@inproceedings{hong2024metagpt,
  title = {MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework},
  author = {Hong, Sirui and Chen, Jonathan and Zhu, Ceyao and others},
  booktitle = {ICLR},
  year = {2024}
}
```

PDF: `docs/MetaGPT-Mini-Learning-Guide.pdf`
Repo: https://github.com/mannuking/metagpt-mini