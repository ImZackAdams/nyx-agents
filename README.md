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
python -m lilbot
python -m lilbot "why is my system slow?"
python -m lilbot repo summarize .
python -m lilbot repo trace-function authenticate_user .
python -m lilbot logs analyze /var/log/syslog
python -m lilbot explain-command "tar -czf backup.tar.gz project/"
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

For GPU-first usage with the bundled Falcon model, install the optional extras:

```bash
pip install -e ".[hf,quantization]"
```

## CLI Usage

Interactive chat:

```bash
python -m lilbot --device cuda --quantize-4bit
```

That starts a local chat loop. Type `clear` to reset the current conversation context or `exit` to leave.

One-shot reasoning:

```bash
python -m lilbot --model /path/to/local/model --device cuda --quantize-4bit --verbose "why is my system slow?"
python -m lilbot --backend hf --device cpu "explain the largest files in this repository"
```

Deterministic subcommands:

```bash
python -m lilbot repo summarize .
python -m lilbot repo trace-function authenticate_user .
python -m lilbot logs analyze /var/log/syslog
python -m lilbot explain-command "iptables -A INPUT -p tcp --dport 22 -j ACCEPT"
```

Useful flags:

- `--model` local model path or cached offline model identifier
- `--backend` backend selector, currently `hf`
- `--device` `auto`, `cpu`, or `cuda`
- `--quantize-4bit` enable 4-bit GPU loading when `bitsandbytes` is available
- `--max-steps` controller step limit
- `--max-new-tokens` generation limit per model step
- `--temperature` sampling temperature
- `--verbose` emit `[STEP]`, `[RAW]`, `[THOUGHT]`, `[ACTION]`, `[ARGS]`, and `[OBSERVATION]` logs

For large local checkpoints on smaller GPUs, the recommended path is:

```bash
python -m lilbot --device cuda --quantize-4bit
```

If `--device auto` picks CUDA and the model still does not fit, Lilbot falls back to CPU automatically during model load.

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
