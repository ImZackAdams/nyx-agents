# Lilbot

`lilbot` is a local-first CLI assistant for two jobs:

- inspect the workspace you are currently in
- remember durable notes, profile facts, and session history locally

It is intentionally narrower than a coding agent. The point is to be useful fast, stay understandable, and still get better when you add a local model.

## Why It Is Different

- `Useful before model setup`
  Deterministic commands and direct-answer routes work without `torch`, `transformers`, or a configured model.
- `Local by default`
  Workspace inspection stays inside the workspace root, and memory stays on your machine.
- `Transparent tool use`
  When Lilbot uses a tool, it prints the tool call to `stderr`.
- `Small enough to extend`
  The runtime is a compact Python CLI with explicit tool definitions and regression tests.

## Quick Start

Install the base CLI:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m lilbot init
```

Try the no-model flow immediately:

```bash
python -m lilbot "what files are in this project?"
python -m lilbot note "buy milk"
python -m lilbot "what notes do I have?"
python -m lilbot doctor
```

Add local-model support only when you want it:

```bash
pip install -e ".[hf]"
```

Add 4-bit GPU quantization support:

```bash
pip install -e ".[hf,quantization]"
```

## First Run Experience

If no model is configured, Lilbot does not dump a useless placeholder anymore. It gives setup guidance and points you toward deterministic features that already work.

Two commands matter on day one:

- `python -m lilbot init`
  Creates Lilbot's user data directories and copies `.env.example` to `.env` when a template exists in the current directory.
- `python -m lilbot doctor`
  Shows workspace root, memory paths, model path status, dependency checks, and next steps.

## A Short Demo

```text
$ python -m lilbot
Request (or 'exit'): my name is Zack
[lilbot] tool save_profile_memory {"category": "name", "text": "name: Zack"}

Okay. I'll remember that your name is Zack.

Request (or 'exit'): what is my name?
[lilbot] tool search_profile {"limit": 8, "query": "name"}

Your name appears to be Zack.

Request (or 'exit'): what files are in this project?
[lilbot] tool list_files {"max_entries": 50, "path": "."}

.env.example
README.md
lilbot/
tests/
```

## Core Workflows

### 1. Deterministic Commands

Commands starting with `!` skip the model entirely.

- `!help`
- `!ls [path]`
- `!read <file>`
- `!sys`
- `!note <text>`
- `!notes [query]`
- `!remember <text>`
- `!profile [query]`
- `!history [query]`
- `!doctor`
- `!init`

These also work as inline commands:

```bash
python -m lilbot ls
python -m lilbot read README.md
python -m lilbot notes groceries
```

### 2. Deterministic Direct Answers

Some natural-language requests bypass model generation because local logic is already enough.

Examples:

- `what is my name?`
- `what do you know about me?`
- `what is my session id?`
- `what is in this directory?`
- `summarize this repo`

### 3. Agent Mode

If a request is not satisfied by the first two lanes, Lilbot can use a local model plus a small tool surface:

- file listing
- file reading
- notes save/search
- profile save/search
- session-history search
- system info

The protocol is deliberately tiny:

```text
FINAL: <answer>
TOOL: <tool_name> <json object>
```

## Installation Notes

The base install is intentionally light:

- `python-dotenv`
- `psutil`

Model dependencies are optional:

- `.[hf]` adds `torch`, `transformers`, and `accelerate`
- `.[hf,quantization]` also adds `bitsandbytes`

This makes `pip install -e .` or `pipx install .` practical for people who want the CLI and deterministic workflows first.

## Storage Defaults

Lilbot no longer stores state inside the package directory by default.

- memory defaults to the OS app-data directory
- on Linux that is typically `~/.local/share/lilbot/`
- the default SQLite database lives under `memory/memory_store.db`
- the default model directory is `models/default`
- if the OS app-data directory is unavailable, Lilbot falls back to `.lilbot/` in the current working directory

You can override these with:

```bash
LILBOT_HOME=
LILBOT_MEMORY_DB_PATH=
LILBOT_MEMORY_JSON_PATH=
LILBOT_MODEL_PATH=
```

## Current Boundaries

Lilbot is intentionally read-heavy and local.

It does not currently provide:

- web browsing
- arbitrary shell execution
- file editing
- long-horizon autonomous planning
- note/profile deletion commands

## Development

Run the regression suite:

```bash
python -m unittest discover -s tests -v
```

Important files:

- `lilbot/cli/main.py`
- `lilbot/cli/agent.py`
- `lilbot/cli/_agent_policy.py`
- `lilbot/cli/_agent_protocol.py`
- `lilbot/llm/provider.py`
- `lilbot/memory/memory.py`
- `lilbot/tools/`

## Project Docs

- [GETTING_STARTED.md](GETTING_STARTED.md)
- [HOWTOUSE.md](HOWTOUSE.md)
- [ROADMAP.md](ROADMAP.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [.env.example](.env.example)

## License

MIT. See [LICENSE](LICENSE).
