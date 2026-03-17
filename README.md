# Lilbot

Most "AI tools" are just web wrappers around someone else's GPU bill.

Lilbot is not that.

Lilbot is a local-first AI command line assistant for developers and system administrators. It runs the model on your machine, inside Python, under your control. No OpenAI API. No cloud dependency. No hosted agent stack pretending to be infrastructure.

This is what an AI-native terminal utility is supposed to look like:

- local model
- explicit controller loop
- deterministic tools
- visible reasoning traces
- safe-by-default shell access
- no mystery backend doing cute things behind your back

If you want a chatbot tab in a browser, this is the wrong project. If you want a machine-local operator that can inspect repos, logs, and system state without shipping your environment to a vendor, this is the right one.

## What Lilbot Actually Does

Lilbot is built for real terminal work:

- understand repositories
- trace functions through source trees
- inspect system state
- summarize logs
- explain shell commands
- help reason about broken local dev environments

Examples:

```bash
python -m lilbot
python -m lilbot "why is my system slow?"
python -m lilbot repo summarize .
python -m lilbot repo trace-function authenticate_user .
python -m lilbot logs analyze /var/log/syslog
python -m lilbot explain-command "tar -czf backup.tar.gz project/"
```

## Why This Exists

Because the default pattern for AI dev tooling is bad.

People keep building systems where the language model is allowed to pretend it knows the machine. It doesn't. The model should reason. The program should inspect reality. Python should stay in charge of tools, safety, validation, and formatting.

Lilbot keeps that boundary clean:

- the model does not execute commands directly
- tools are deterministic and explicit
- the controller loop is visible and debuggable
- safety policy is code, not vibes

That is the whole game.

## Architecture

Lilbot is split into parts that are boring in the good way:

- CLI in `lilbot/cli.py`
- agent wrapper in `lilbot/agent.py`
- explicit controller loop in `lilbot/controller.py`
- prompt construction in `lilbot/prompts.py`
- model backend abstraction in `lilbot/model/`
- plugin-style tools in `lilbot/tools/`
- shell safety policy in `lilbot/safety/`
- observability helpers in `lilbot/utils/`
- session memory in `lilbot/memory/`
- retrieval stubs in `lilbot/retrieval/`

The current backend is Hugging Face Transformers. The design keeps the backend boundary clean so you can swap that later without turning the rest of the codebase into soup.

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

Make an environment. Install the package. Point it at a local checkpoint.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Lilbot expects a local Hugging Face checkpoint. You can provide one explicitly:

```bash
export LILBOT_MODEL=/path/to/local/model
export LILBOT_DEVICE=cpu
```

If you keep a checkpoint under `lilbot/models/<model-name>`, Lilbot will auto-discover it.

If you want GPU-first inference with 4-bit loading:

```bash
pip install -e ".[hf,quantization]"
```

## Usage

### Interactive Mode

Run this:

```bash
python -m lilbot --device cuda --quantize-4bit
```

That starts the local chat loop. Type `clear` to wipe the current conversation context. Type `exit` to leave.

### One-Shot Queries

Use this when you want an answer and then you want your shell prompt back:

```bash
python -m lilbot --model /path/to/local/model --device cuda --quantize-4bit --verbose "why is my system slow?"
python -m lilbot --backend hf --device cpu "explain the largest files in this repository"
```

### Deterministic Subcommands

These do not need the full agent loop:

```bash
python -m lilbot repo summarize .
python -m lilbot repo trace-function authenticate_user .
python -m lilbot logs analyze /var/log/syslog
python -m lilbot explain-command "iptables -A INPUT -p tcp --dport 22 -j ACCEPT"
```

### Useful Flags

- `--model` local model path or cached offline model identifier
- `--backend` backend selector, currently `hf`
- `--device` `auto`, `cpu`, or `cuda`
- `--quantize-4bit` enable 4-bit GPU loading when `bitsandbytes` is available
- `--max-steps` controller step limit
- `--max-new-tokens` generation cap per model step
- `--temperature` sampling temperature
- `--verbose` print `[STEP]`, `[RAW]`, `[THOUGHT]`, `[ACTION]`, `[ARGS]`, and `[OBSERVATION]`

## Performance Notes

Big local checkpoints are not magic. If you want good latency, stop pretending a giant model on weak settings is going to feel snappy.

The practical path is:

```bash
python -m lilbot --device cuda --quantize-4bit
```

If responses still feel heavy:

- make sure `bitsandbytes` is actually installed
- use `--device cuda --quantize-4bit` instead of hoping `auto` guesses right
- reduce generation with `--max-new-tokens 128`
- use `clear` in interactive mode when the conversation gets stale

If `--device auto` picks CUDA and the checkpoint still does not fit, Lilbot falls back to CPU during model load.

## Safety Model

This project is local-first, not reckless.

- filesystem tools stay inside the configured workspace root
- log analysis is limited to the workspace or common system log locations
- shell execution is restricted to read-oriented commands
- dangerous patterns like `rm -rf`, `shutdown`, `mkfs`, `dd`, and install-script pipelines are blocked
- the controller enforces a strict `max_steps` limit

The model is not trusted with direct execution authority. Good. It shouldn't be.

## Development

Run the tests:

```bash
python -m unittest discover -s tests -v
```

Lilbot is experimental, but it is trying to be experimental in the useful way: small, modular, inspectable, and grounded in local reality.
