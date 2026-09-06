# MetaGPT-Mini

A clean, from-scratch reimplementation of **MetaGPT** (Hong et al., **ICLR 2024 Oral**, top 1.2%, ranked **#1** in the LLM-Agent category) that runs on **any OpenAI-compatible LLM** — including MiniMax-M3 and Qwen3-8B-Flash.

This is not a wrapper around the original `geekan/MetaGPT`. It is a re-engineered, transparent implementation in ~300 lines that you can read, modify, and demo in front of a class.

## What MetaGPT actually does (and what we re-implement)

MetaGPT encodes **Standard Operating Procedures (SOPs)** from human software teams into prompt sequences. Instead of one mega-agent, you get a **society of role-specialised agents** that collaborate via a shared message pool:

```
User → ProductManager → Architect → Engineer → QA → Code
```

Each agent:
- reads from a shared `MessagePool`
- emits structured `Message` objects with `role`, `content`, and `cause_by`
- only listens to messages from roles it depends on

This is the **#1 cited multi-agent software-engineering pattern** in the literature.

## Project layout

```
metagpt-mini/
├── README.md
├── pyproject.toml
├── .env.example
├── metagpt_mini/
│   ├── __init__.py
│   ├── llm.py          # OpenAI-compatible client (works with MiniMax-M3, Qwen, etc.)
│   ├── schema.py       # Message, Role, MessagePool — the SOP substrate
│   ├── actions.py      # WritePRD, WriteDesign, WriteCode, WriteTest — the verbs
│   ├── roles.py        # ProductManager, Architect, Engineer, QA — the agents
│   ├── team.py         # Team orchestrator: environment + agents + run loop
│   └── utils.py        # Cost tracker + log helpers
├── examples/
│   └── build_cli_app.py   # "Build a CLI todo app" — full end-to-end run
└── tests/
    └── test_schema.py     # Round-trip Message serialization + pool tests
```

## Install + run

```bash
cd /Users/jkm/Projects/metagpt-mini
uv venv
source .venv/bin/activate
uv pip install -e .

# Configure your LLM (see .env.example)
cp .env.example .env
$EDITOR .env           # set LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

# Run the canonical demo
python examples/build_cli_app.py
```

## LLM-agnostic by design

The framework only knows the OpenAI Chat Completions API. Any provider that exposes it works out of the box:

| Provider | `LLM_BASE_URL` | `LLM_MODEL` example |
|----------|----------------|----------------------|
| MiniMax-M3 (cloud) | `https://api.minimax.chat/v1` | `MiniMax-M3` |
| Qwen3-8B-Flash (cloud) | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen3-8b-flash` |
| Local Ollama | `http://localhost:11434/v1` | `qwen2.5-coder:7b` |
| LM Studio | `http://localhost:1234/v1` | any |

## Reference

```bibtex
@inproceedings{hong2024metagpt,
  title={MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework},
  author={Hong, Sirui and Zhange, Xiawu and Chen, Jonathan and Chen, Junnan and
          Jin, Yuheng and Zhang, Steven and Zhu, Ceyao and Cai, Zhen and
          others},
  booktitle={ICLR},
  year={2024}
}
```

PDF: `../agentic_engineering_top5/02_metagpt.pdf`