# How To Use Lilbot

`lilbot` is a local command-line assistant with three layers:

1. deterministic `!` commands
2. deterministic direct-answer routing for common requests
3. a local-model agent loop for everything else

This guide is the long-form manual for using those layers well.

## What Lilbot Is For

Lilbot is designed for grounded, local workflows rather than open-ended autonomy.

Use it when you want to:

- inspect and summarize a local repository
- keep personal memory in a local SQLite store
- search earlier conversation by session
- manage notes without leaving the terminal
- combine a local model with a small, transparent toolset

Do not think of Lilbot as:

- a web browser
- a shell agent
- a file editor
- a task scheduler
- a fully autonomous coding agent

It is intentionally narrower than that.

## The Mental Model

Most confusion disappears once you understand the three runtime lanes.

### Lane 1: Prefix Commands

Anything that begins with `!` is handled locally and deterministically.

Examples:

```bash
!ls
!read README.md
!notes groceries
!profile
```

These commands do not need the model.

### Lane 2: Deterministic Direct Answers

Some natural-language requests are answered without full generation because local logic is already sufficient.

Examples:

- `what is my name?`
- `what do you know about me?`
- `what is my session id?`
- `what is your name?`
- `summarize this repo`
- `what is in this directory?`

This keeps obvious workflows fast and reduces local-model drift.

### Lane 3: Agent Mode

If a request is not satisfied by lanes 1 or 2, Lilbot runs the LLM agent loop.

The model can ask for one tool at a time using a tiny protocol:

```text
FINAL: <answer>
TOOL: <tool_name> <json object>
```

Lilbot executes the tool, appends the observation, and continues until the model reaches a final answer or hits the tool-step limit.

## Installation

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Optional CUDA quantization support:

```bash
pip install bitsandbytes
```

`python-dotenv` is included by the main requirements, so `.env` loading works after a normal install.

## Local Model Setup

Lilbot uses a local Hugging Face model backend when it can find a model path.

Provide a model path explicitly:

```bash
export LILBOT_MODEL_PATH=/path/to/local/model
```

Or:

```bash
python3 -m lilbot --model-path /path/to/local/model
```

If `lilbot/models/falcon3_10b_instruct` exists, Lilbot will use it automatically by default.

If no model path is available, Lilbot falls back to the lightweight echo backend. That is useful for CLI and test flows, but not for real answers.

## Configuration

Lilbot loads `.env` automatically when `python-dotenv` is available.

The project includes an [.env.example](.env.example) showing the supported environment variables.

Common configuration:

```bash
LILBOT_BACKEND=auto
LILBOT_MODEL_PATH=
TEXT_MODEL_PATH=
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
LILBOT_WORKSPACE_ROOT=
LILBOT_MEMORY_DB_PATH=
LILBOT_MEMORY_JSON_PATH=
```

### Main Settings

`LILBOT_BACKEND`

- `auto`: prefer the local Hugging Face backend, otherwise use echo
- `hf`: require a real local model
- `echo`: never load a real model

`LILBOT_DEVICE`

- `auto`: prefer CUDA when available
- `cpu`: force CPU inference
- `cuda`: fail if CUDA is unavailable

`LILBOT_MAX_NEW_TOKENS`

- caps reply length
- defaults to `96`
- raise it for fuller answers
- lower it if you need lower latency

`LILBOT_QUANTIZE_4BIT`

- only matters for CUDA-backed Hugging Face inference
- requires `bitsandbytes`

`LILBOT_DO_SAMPLE`

- `0` means greedy decoding
- `1` enables sampling

`LILBOT_STREAM`

- `1` enables safe direct-answer streaming
- `0` buffers replies until completion

`LILBOT_MAX_AGENT_STEPS`

- limits how many tools the agent may call for one request

`LILBOT_HISTORY_MESSAGES`

- controls how many recent messages are loaded into the in-memory working context

`LILBOT_SESSION_ID`

- selects the current persistent session

`LILBOT_WORKSPACE_ROOT`

- restricts file tools to a chosen root
- defaults to the directory where Lilbot starts

## Starting Lilbot

### Interactive REPL

```bash
python3 -m lilbot
```

You will see:

```text
Request (or 'exit'):
```

Local REPL commands:

- `exit` or `quit`: leave the session
- `clear` or `cls`: clear the screen
- `help`, `commands`, or `?`: show command help without invoking the model

### Explicit Interactive Mode

```bash
python3 -m lilbot run
```

### One-Shot Prompt

```bash
python3 -m lilbot --prompt "What do you know about me?"
```

### Inline Request Without `--prompt`

```bash
python3 -m lilbot "summarize this repo"
python3 -m lilbot ls
python3 -m lilbot profile
```

Lilbot rewrites known inline commands such as `ls`, `read`, `notes`, and `profile` into the corresponding deterministic handlers.

### Supplying a System Prompt

```bash
python3 -m lilbot --system "Keep answers terse." --prompt "Explain this codebase"
```

## Bash `!` Gotcha

In interactive `bash`, `!` triggers shell history expansion.

So this may fail:

```bash
python3 -m lilbot !ls
```

Use one of these instead:

```bash
python3 -m lilbot --prompt '!ls'
python3 -m lilbot ls
```

Inside the Lilbot REPL itself, `!ls` works normally.

## Prefix Commands

Prefix commands are the deterministic, model-free tool layer.

### `!help`

Show the built-in command list.

Examples:

```bash
!help
python3 -m lilbot help
```

### `!ls [path]`

List files under the workspace root.

Examples:

```bash
!ls
!ls lilbot
python3 -m lilbot ls lilbot
```

Notes:

- shell flags like `-la` are ignored
- paths outside the workspace root are refused
- very large directories are truncated

### `!read <file>`

Read a text file under the workspace root.

Examples:

```bash
!read README.md
!read lilbot/cli/main.py
python3 -m lilbot read README.md
```

Notes:

- binary files are not dumped
- large files are truncated
- paths outside the workspace root are refused

### `!sys`

Show basic local system information.

Typical output includes:

- OS
- Python version
- current directory
- CPU usage, when `psutil` is available
- RAM usage, when `psutil` is available

Examples:

```bash
!sys
python3 -m lilbot sys
```

### `!note <text>`

Save a general note.

Use notes for:

- reminders
- shopping lists
- project facts
- recurring tasks
- information that is useful but not really part of your identity

Examples:

```bash
!note Buy oat milk
!note Project alpha uses SQLite
python3 -m lilbot note "Pick up coffee beans on Friday"
```

### `!notes [query]`

List recent notes or search them.

Examples:

```bash
!notes
!notes coffee
python3 -m lilbot notes groceries
```

### `!remember <text>`

Save a durable personal memory.

Use this for stable facts about you:

- your name
- timezone
- preferences
- goals
- recurring personal facts

Examples:

```bash
!remember my name is Zack
!remember my timezone is America/New_York
!remember I prefer concise answers
```

### `!profile [query]`

List recent profile memories or search them.

Examples:

```bash
!profile
!profile name
!profile preferences
python3 -m lilbot profile timezone
```

### `!history [query]`

List or search persistent session history for the current session.

Examples:

```bash
!history
!history roadmap
python3 -m lilbot --session-id work history decision
```

This command is always scoped to the active session id.

## Memory-First Workflows

Lilbot works best when you think about memory in three buckets.

### Profile Memory

Profile memory is for stable facts about you.

Good profile memory:

- `my name is Zack`
- `my timezone is America/New_York`
- `I prefer concise answers`
- `my favorite editor is Neovim`
- `my goal is to finish the lilbot CLI`

You can save profile memory either by talking naturally:

```bash
python3 -m lilbot "my name is Zack"
```

Or explicitly:

```bash
python3 -m lilbot remember "my timezone is America/New_York"
```

Then later:

```bash
python3 -m lilbot "what is my name?"
python3 -m lilbot "what do you know about me?"
```

### Notes

Notes are for general durable information that is useful to store, but not really part of your profile.

Good notes:

- `buy milk`
- `project alpha uses SQLite`
- `look into llama.cpp next week`
- `remember to call the dentist`

Examples:

```bash
python3 -m lilbot note "buy milk"
python3 -m lilbot notes
python3 -m lilbot "what notes do I have?"
```

### Session History

Session history preserves prior conversation inside a named thread.

Examples:

```bash
python3 -m lilbot --session-id work
python3 -m lilbot --session-id personal
```

That keeps conversation state separate across contexts.

### Current Memory Limitations

Right now Lilbot does not yet support:

- deleting notes from the CLI
- deleting profile memories from the CLI
- editing memory entries in place
- scheduled reminders

The current memory model is intentionally simple and local.

## Deterministic Direct Answers

Lilbot intentionally bypasses the model for a set of requests where local logic is enough.

That includes requests such as:

- `what is my name?`
- `what do you know about me?`
- `what is your name?`
- `what is my session id?`
- `summarize this repo`
- `what is in this directory?`

This matters because:

- the answer is usually faster
- the model is not loaded unnecessarily
- common local-model mistakes are avoided

## Agent Mode in Detail

If a prompt is not satisfied by deterministic logic, Lilbot enters the model-backed agent loop.

### What the Agent Can Do

The current tool registry includes:

- file listing
- file reading
- system information
- note save and search
- profile save and search
- session-history search

### What the Agent Cannot Yet Do

- edit files
- run arbitrary shell commands
- browse the web
- delete memory entries

### Tool Visibility

When Lilbot uses a tool, it prints a line to `stderr`.

Example:

```text
[lilbot] tool read_file {"max_chars": 2000, "path": "README.md"}
```

This makes it easy to tell whether a reply was grounded in local inspection or came straight from the model.

### Guardrails

Lilbot includes several guardrails:

- repeated identical tool calls are blocked
- malformed tool output is normalized where possible
- repo summaries can fall back to deterministic directory summaries
- personal-fact answers must come from saved profile memory, notes, or history
- workspace file access is restricted to the workspace root

## Workspace Root

File tools are bounded to a workspace root.

By default, the workspace root is the directory where you start Lilbot.

Example:

```bash
cd ~/Desktop/lilbot
python3 -m lilbot
```

In that case, all file reads and listings are restricted to `~/Desktop/lilbot`.

You can override the root:

```bash
export LILBOT_WORKSPACE_ROOT=~/projects
python3 -m lilbot
```

## Performance Tuning

Performance depends mostly on your model, hardware, and reply budget.

### Sensible Local Defaults

For a Falcon-style local setup, these defaults are pragmatic:

```bash
LILBOT_BACKEND=auto
LILBOT_DEVICE=auto
LILBOT_QUANTIZE_4BIT=1
LILBOT_DO_SAMPLE=0
LILBOT_STREAM=1
LILBOT_MAX_NEW_TOKENS=96
```

### If Replies Feel Too Slow

Try:

- lowering `LILBOT_MAX_NEW_TOKENS`
- keeping greedy decoding with `LILBOT_DO_SAMPLE=0`
- ensuring CUDA is actually available
- enabling 4-bit quantization when supported
- switching to a smaller model

### If Replies Feel Too Short

Raise the budget:

```bash
python3 -m lilbot --max-new-tokens 160 "Explain the current memory system"
```

Or:

```bash
export LILBOT_MAX_NEW_TOKENS=160
```

### If the First Real Request Feels Slower

In interactive mode, Lilbot delays model loading until a request actually needs the model.

That means:

- deterministic commands feel instant
- the first real model-backed request pays the model load cost
- later model-backed requests in the same process are faster

### If the Model Should Use the GPU but Does Not

Try:

```bash
python3 -m lilbot --device cuda
```

That forces a clear failure when CUDA is unavailable instead of silently falling back.

## Troubleshooting

### I only get `(echo provider) No model configured.`

Lilbot could not find or initialize a real model.

Check:

- `LILBOT_MODEL_PATH`
- `TEXT_MODEL_PATH`
- `--model-path`
- whether `lilbot/models/falcon3_10b_instruct` exists
- whether `torch`, `transformers`, and `accelerate` are installed

### Replies are clipped

Raise the token budget:

```bash
python3 -m lilbot --max-new-tokens 160
```

Or set:

```bash
export LILBOT_MAX_NEW_TOKENS=160
```

### `!` commands fail in bash

That is shell history expansion.

Use:

```bash
python3 -m lilbot --prompt '!ls'
```

Or:

```bash
python3 -m lilbot ls
```

### The assistant starts giving stale or weird answers

Persistent session history can carry bad outputs forward inside the same session.

If a session feels polluted, start a fresh one:

```bash
python3 -m lilbot --session-id fresh
```

### File access is unexpectedly refused

Check:

- the current working directory
- `LILBOT_WORKSPACE_ROOT`
- whether the path is outside the workspace root

### CPU replies are very slow

That is expected for larger local models.

Use CUDA if possible, reduce the model size, or lower `max_new_tokens`.

### You want to stop generation

Press `Ctrl+C`.

Lilbot handles generation cancellation cleanly and returns to the prompt.

## Extending Lilbot

The project is intentionally simple to extend.

### Adding a Tool

General pattern:

1. implement a function in `lilbot/tools/`
2. add a tool definition with `name`, `description`, `parameters`, `example`, and `execute`
3. register it in `lilbot/tools/__init__.py`
4. optionally add a matching prefix command in `lilbot/cli/main.py`
5. add tests
6. update docs

### Key Files

- `lilbot/cli/main.py`
  CLI entrypoint, parser, REPL, one-shot mode, and prefix commands
- `lilbot/cli/agent.py`
  agent loop orchestration
- `lilbot/cli/_agent_policy.py`
  routing heuristics, deterministic answers, and fallbacks
- `lilbot/cli/_agent_prompting.py`
  prompt construction
- `lilbot/cli/_agent_protocol.py`
  `FINAL:` / `TOOL:` parsing and stream normalization
- `lilbot/llm/provider.py`
  backend and local model loading
- `lilbot/memory/memory.py`
  SQLite-backed notes, profile memory, and session history
- `tests/`
  regression coverage

### Safety Posture for Future Tools

If you add write-capable tools later, keep the current posture:

- default to read-only when possible
- require explicit user intent for writes
- keep workspace boundaries clear
- add deterministic error messages
- add regression coverage before widening capability

## Running Tests

Run the regression suite:

```bash
python -m unittest discover -s tests -v
```

## Short Cheat Sheet

```bash
python3 -m lilbot
python3 -m lilbot --prompt "Hello"
python3 -m lilbot "summarize this repo"
python3 -m lilbot "what is in this directory?"
python3 -m lilbot "my name is Zack"
python3 -m lilbot "what do you know about me?"
python3 -m lilbot --session-id work "what did we decide earlier?"
python3 -m lilbot ls
python3 -m lilbot read README.md
python3 -m lilbot notes
python3 -m lilbot remember "my timezone is America/New_York"
python3 -m lilbot profile
python3 -m lilbot history
```
