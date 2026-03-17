# Lilbot

Lilbot is a local-first AI command line assistant for developers and system administrators.

It runs a local language model directly inside Python, treats that model as a reasoning engine, and keeps tool execution, safety checks, and formatting under explicit system control. Lilbot is not a cloud assistant, not a web app, and not a thin chatbot wrapper.

## Philosophy

- fully local runtime
- no OpenAI APIs
- no cloud APIs
- no hosted model servers
- modular tool architecture
- safe-by-default shell access
- debuggable controller loop with visible step traces

## What Lilbot Does

Lilbot is built for practical terminal tasks such as:

- understanding repositories
- inspecting system state
- summarizing logs
- explaining shell commands
- tracing functions in code
- helping reason about local developer environments

Example commands:

```bash
python cli.py "why is my system slow?"
python cli.py repo summarize .
python cli.py repo trace-function authenticate_user .
python cli.py logs analyze /var/log/syslog
python cli.py explain-command "tar -czf backup.tar.gz project/"
```

## Architecture

Lilbot separates the runtime into clear layers:

- CLI layer in `lilbot/cli.py`
- agent wrapper in `lilbot/agent.py`
- explicit controller loop in `lilbot/controller.py`
- prompt construction in `lilbot/prompts.py`
- model backend abstraction in `lilbot/model/`
- plugin-style tools in `lilbot/tools/`
- safety policy in `lilbot/safety/`
- observability helpers in `lilbot/utils/`
- session memory in `lilbot/memory/`
- retrieval stubs in `lilbot/retrieval/`

The model never executes commands directly. It can only reason, choose a tool, and react to deterministic observations returned by Python.

## Directory Tree

```text
.
├── cli.py
├── README.md
├── requirements.txt
├── pyproject.toml
├── lilbot
│   ├── __init__.py
│   ├── __main__.py
│   ├── agent.py
│   ├── cli.py
│   ├── config.py
│   ├── controller.py
│   ├── prompts.py
│   ├── model
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── hf_model.py
│   ├── tools
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── filesystem.py
│   │   ├── logs.py
│   │   ├── registry.py
│   │   ├── repo.py
│   │   ├── shell.py
│   │   └── system.py
│   ├── safety
│   │   ├── __init__.py
│   │   └── shell_policy.py
│   ├── utils
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── formatting.py
│   │   └── logging.py
│   ├── retrieval
│   │   ├── __init__.py
│   │   ├── chunking.py
│   │   ├── embeddings.py
│   │   └── index.py
│   └── memory
│       ├── __init__.py
│       └── session.py
└── tests
    ├── test_agent_loop.py
    ├── test_shell_policy.py
    └── test_tools.py
```

## Setup

Create a virtual environment and install the local inference dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Lilbot expects a local Hugging Face checkpoint. You can point it at a model directory or a model already cached offline:

```bash
export LILBOT_MODEL=/path/to/local/model
export LILBOT_DEVICE=cpu
```

If you keep a checkpoint under `lilbot/models/<model-name>`, Lilbot will auto-discover it.

## CLI Usage

Free-form reasoning:

```bash
python cli.py --model /path/to/local/model --verbose "why is my system slow?"
python -m lilbot --backend hf --device cpu "explain the largest files in this repository"
```

Deterministic subcommands:

```bash
python cli.py repo summarize .
python cli.py repo trace-function authenticate_user .
python cli.py logs analyze /var/log/syslog
python cli.py explain-command "iptables -A INPUT -p tcp --dport 22 -j ACCEPT"
```

Useful flags:

- `--model` local model path or cached offline model identifier
- `--backend` backend selector, currently `hf`
- `--device` `auto`, `cpu`, or `cuda`
- `--max-steps` controller step limit
- `--max-new-tokens` generation limit per model step
- `--temperature` sampling temperature
- `--verbose` emit `[STEP]`, `[RAW]`, `[THOUGHT]`, `[ACTION]`, `[ARGS]`, and `[OBSERVATION]` logs

## Safety Model

- filesystem tools are restricted to the configured workspace root
- log analysis is restricted to the workspace or common system log directories
- shell execution runs in restricted mode with allowlisted read-oriented commands
- dangerous patterns such as `rm -rf`, `shutdown`, `mkfs`, `dd`, and install-script pipelines are blocked
- the controller enforces a strict `max_steps` limit

## Development

Run the regression suite with:

```bash
python -m unittest discover -s tests -v
```

Lilbot is still experimental, but the structure is intended to be the start of a serious AI-native terminal utility rather than a toy demo.
