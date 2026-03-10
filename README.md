# Lilbot

`lilbot` is a local-first CLI assistant that can inspect your workspace, remember stable facts about you, and use local tools before it answers.

It sits in a practical middle ground:

- more useful than a plain local chatbot
- simpler and safer than a fully autonomous agent
- especially good at workspace inspection, personal memory, and session continuity

For the full operating guide, examples, troubleshooting, and extension notes, see [HOWTOUSE.md](HOWTOUSE.md).

## What Lilbot Is Good At

Lilbot currently shines in four areas:

- `Local workspace help`
  Read files, list directories, summarize a repository, and answer questions grounded in the current workspace.
- `Memory-first assistance`
  Keep durable profile memories, general notes, and session history in SQLite.
- `Deterministic command handling`
  Built-in `!` commands bypass the model and run local tools directly.
- `Model-assisted tool use`
  For normal prompts, the LLM can inspect files, search notes, search profile memory, search session history, and then answer.

## Quick Start

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional CUDA quantization support:

```bash
pip install bitsandbytes
```

Start the interactive CLI:

```bash
python3 -m lilbot
```

Run a one-shot prompt:

```bash
python3 -m lilbot --prompt "Summarize this repository"
```

Use an inline request without `--prompt`:

```bash
python3 -m lilbot "What do you know about me?"
python3 -m lilbot ls
python3 -m lilbot read README.md
```

## Killer Demo

One short session shows what Lilbot is for:

```text
$ python3 -m lilbot
Request (or 'exit'): my name is Zack
[lilbot] tool save_profile_memory {"category": "name", "text": "name: Zack"}

Okay. I'll remember that your name is Zack.

Request (or 'exit'): what is my name?
[lilbot] tool search_profile {"limit": 8, "query": "name"}
[lilbot] tool search_notes {"limit": 5, "query": "name"}
[lilbot] tool search_history {"limit": 6, "query": "name", "session_id": "default"}

Your name appears to be Zack.

Request (or 'exit'): summarize this repo
[lilbot] tool list_files {"max_entries": 50, "path": "."}

This repository appears to be a Python CLI project. The main application code lives in `lilbot/`.
```

That is the core loop: remember something durable, retrieve it deterministically later, and inspect the local repo when a prompt depends on local files.

## First Examples

```bash
python3 -m lilbot "what is in this directory?"
python3 -m lilbot "summarize this repo"
python3 -m lilbot "my name is Zack"
python3 -m lilbot "what is my name?"
python3 -m lilbot "what do you know about me?"
python3 -m lilbot --session-id work "what did we decide earlier?"
```

## Interaction Model

Lilbot has three practical lanes:

### 1. Prefix Commands

Commands that begin with `!` run local handlers directly.

Available commands:

- `!help`
- `!ls [path]`
- `!read <file>`
- `!sys`
- `!note <text>`
- `!notes [query]`
- `!remember <text>`
- `!profile [query]`
- `!history [query]`

These do not require the model.

### 2. Deterministic Direct Answers

Some requests are answered without model generation when local logic is enough. Examples include:

- profile lookups such as `what is my name?`
- profile summaries such as `what do you know about me?`
- repository and directory listing summaries
- session-id questions
- assistant identity questions such as `what is your name?`

This keeps common workflows fast and reduces model sloppiness.

### 3. Agent Mode

Everything else goes through the agent loop. The model can choose a local tool, see the result, and continue until it returns a final answer.

Lilbot prints tool activity to `stderr` as it happens so you can see what the agent is doing.

## Agent Loop Architecture

The runtime path is intentionally small and explicit:

```text
user request
   |
   v
lilbot/cli/main.py
   |
   +--> prefix command? ------------------> local handler --> output
   |
   +--> deterministic direct answer? ----> local policy --> output
   |
   +--> agent mode
           |
           v
      lilbot/cli/agent.py
           |
           +--> prefetch local context
           |      - profile memory
           |      - notes
           |      - session history
           |
           +--> build prompt
           |      - lilbot/cli/_agent_prompting.py
           |
           +--> model response parser
           |      - lilbot/cli/_agent_protocol.py
           |
           +--> TOOL request? ---------> lilbot/tools/__init__.py
           |                                |
           |                                +--> filesystem tools
           |                                +--> notes tools
           |                                +--> profile tools
           |                                +--> history tools
           |                                +--> system tools
           |                                         |
           |                                         v
           |                                  lilbot/memory/memory.py
           |
           +--> observation appended
           |
           +--> FINAL answer or deterministic fallback
```

The main responsibilities are split like this:

- `lilbot/cli/main.py`
  CLI entrypoint, REPL, one-shot mode, prefix-command routing, provider loading
- `lilbot/cli/agent.py`
  agent loop orchestration
- `lilbot/cli/_agent_policy.py`
  deterministic routing, memory-prefetch heuristics, and fallback behavior
- `lilbot/cli/_agent_prompting.py`
  the prompt that tells the model how to use tools
- `lilbot/cli/_agent_protocol.py`
  parsing and stream normalization for `FINAL:` / `TOOL:`
- `lilbot/tools/`
  deterministic local tools
- `lilbot/memory/memory.py`
  SQLite-backed storage for notes, profile memory, and session history

## Memory Model

Lilbot stores three kinds of memory:

| Memory Type | Purpose | Typical Examples |
| --- | --- | --- |
| `Profile memory` | Stable facts about you | name, timezone, preferences, goals |
| `Notes` | Durable general notes | reminders, project facts, shopping items |
| `Session history` | Prior messages inside a named conversation | "what did we decide earlier?" |

Default storage is SQLite at `lilbot/memory/memory_store.db`.

Profile memory is intended for "about me" facts. Notes are broader and better for reminders or reference material. Session history preserves recent conversational context within a session.

## Tool Surface

Lilbot currently exposes these tool families:

| Tool | Purpose |
| --- | --- |
| `list_files` | List directory contents under the workspace root |
| `read_file` | Read a text file under the workspace root |
| `system_info` | Show OS, Python version, cwd, and optional CPU/RAM usage |
| `save_note` / `search_notes` | Store and retrieve general notes |
| `save_profile_memory` / `search_profile` | Store and retrieve personal profile memory |
| `search_history` | Retrieve prior conversation from the current session |

The current toolset is intentionally read-oriented. Lilbot does not yet edit files, run arbitrary shell commands, or delete memory entries.

## Safety and Boundaries

Lilbot is designed to stay understandable:

- file access is restricted to the workspace root
- profile, note, and history retrieval are local only
- repeated identical tool calls are blocked
- malformed protocol responses are normalized where possible
- deterministic fallbacks are used for directory listings, repo summaries, and similar fragile prompts
- personal-fact answers are grounded in saved profile memory, notes, or history instead of guessing

## Model and Backend

Lilbot supports three backend modes:

- `auto`
  Use the local Hugging Face backend if a model path is available, otherwise fall back to the lightweight echo backend.
- `hf`
  Require a local Hugging Face model path.
- `echo`
  Use a placeholder provider for CLI and testing flows.

If `lilbot/models/falcon3_10b_instruct` exists, Lilbot will use it automatically as the default local model path.

The default response budget is `96` new tokens. This is a compromise between latency and avoiding clipped conversational replies. Increase it when you want fuller answers:

```bash
python3 -m lilbot --max-new-tokens 160 "Explain how the CLI works"
```

## Configuration

Lilbot loads `.env` automatically when `python-dotenv` is available.

Common environment variables:

```bash
LILBOT_BACKEND=auto
LILBOT_MODEL_PATH=/path/to/model
LILBOT_DEVICE=auto
LILBOT_MAX_NEW_TOKENS=96
LILBOT_QUANTIZE_4BIT=1
LILBOT_DO_SAMPLE=0
LILBOT_STREAM=1
LILBOT_MAX_AGENT_STEPS=4
LILBOT_HISTORY_MESSAGES=8
LILBOT_SESSION_ID=default
LILBOT_SYSTEM_PROMPT=
LILBOT_LOG_LEVEL=WARNING
LILBOT_WORKSPACE_ROOT=/path/to/workspace
LILBOT_MEMORY_DB_PATH=/path/to/memory_store.db
LILBOT_MEMORY_JSON_PATH=/path/to/legacy_memory_store.json
```

Useful defaults and behaviors:

- greedy decoding is the default
- streaming is enabled by default
- `--device cpu` is supported for CPU-only machines
- `--quantize-4bit` only matters when CUDA and `bitsandbytes` are available
- session history is grouped by `session_id`
- the legacy JSON notes file is imported automatically on first use if present

## Repository Layout

Important directories and files:

- `lilbot/cli/`
  CLI entrypoint, routing, prompting, protocol parsing, and agent loop
- `lilbot/tools/`
  Deterministic local tools
- `lilbot/memory/`
  SQLite-backed notes, profile memory, and session history
- `lilbot/llm/provider.py`
  Backend selection and local Hugging Face loading
- `tests/`
  Regression coverage for CLI, agent behavior, provider selection, and memory

## Current Limitations

Lilbot is intentionally narrow. It does not currently provide:

- web browsing
- arbitrary shell execution
- file editing
- note/profile deletion commands
- long-horizon autonomous planning

Its quality is also still heavily tied to the local model you run.

## Verification

Run the regression suite:

```bash
python -m unittest discover -s tests -v
```

## Related Docs

- [HOWTOUSE.md](HOWTOUSE.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [.env.example](.env.example)

## License

MIT. See [LICENSE](LICENSE).
