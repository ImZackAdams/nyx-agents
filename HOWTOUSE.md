# How To Use Lilbot

`lilbot` is a local command-line assistant built around a local Hugging Face model, a small agent loop, and a handful of safe local tools.

This guide is the detailed version of the README. It covers:

- installation
- model configuration
- interactive and one-shot usage
- built-in `!` commands
- agent behavior
- sessions and persistent memory
- latency tuning
- troubleshooting
- how to extend the project

## What Lilbot Does

`lilbot` has two main interaction modes:

- Prefix commands, such as `!ls` or `!notes`, which run deterministic local tools directly.
- Normal prompts, such as `Summarize this repo`, which go through the LLM agent loop.

When you give a normal prompt, the model can decide to:

1. inspect local files
2. search notes
3. search earlier conversation in the current session
4. inspect system information
5. return a final answer

That makes `lilbot` more useful than a plain text generator, while keeping the behavior bounded and understandable.

## Core Concepts

Before using `lilbot`, it helps to know four concepts.

### 1. Workspace Root

File tools are restricted to a workspace root. By default, that is the directory where you start `lilbot`.

Examples:

```bash
cd ~/Desktop/lilbot
python3 -m lilbot
```

In that case, `!ls`, `!read`, and agent-driven file access are restricted to `~/Desktop/lilbot`.

You can override the root with:

```bash
export LILBOT_WORKSPACE_ROOT=/path/to/workspace
```

### 2. Session ID

Conversation history is grouped by session ID.

Examples:

```bash
python3 -m lilbot --session-id work
python3 -m lilbot --session-id personal
```

Those sessions keep separate persistent histories in the SQLite database.

### 3. Notes vs Session History

`lilbot` stores two kinds of memory:

- Notes: explicit facts you save with `!note` or by asking the model to remember something.
- Session history: prior user and assistant messages within a named session.

Notes are better for durable facts and reminders. Session history is better for recalling what was discussed in a thread.

### 4. Agent Loop

Normal prompts are not sent to the model once and printed blindly. The agent loop in `lilbot/cli/agent.py` asks the model to respond in one of two forms:

```text
FINAL: <answer>
TOOL: <tool_name> <json object>
```

If the model asks for a tool, `lilbot` runs it, appends the observation, and lets the model continue until it reaches a final answer or the step limit.

The agent also has a few safeguards:

- repeated identical tool calls are refused
- malformed role labels such as `[assistant] TOOL: ...` are normalized
- if the model fails after a useful tool result, `lilbot` can fall back to that observation instead of returning a useless protocol error
- summary requests over file contents or directory listings can fall back to deterministic summaries
- personal-fact questions are expected to rely on notes, session history, or tool evidence rather than hallucination

## Installation

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Optional GPU quantization support:

```bash
pip install bitsandbytes
```

If you want `.env` loading, install `python-dotenv`. In this project that is already included through the main requirements.

## Model Setup

`lilbot` expects a local Hugging Face model directory. The directory should contain the model weights, tokenizer files, and model config.

Set it with an environment variable:

```bash
export LILBOT_MODEL_PATH=/path/to/local/model
```

Or pass it per run:

```bash
python3 -m lilbot --model-path /path/to/local/model
```

If `lilbot/models/falcon3_10b_instruct` exists, `lilbot` will use that automatically.

If no model path is available, `lilbot` falls back to the placeholder `EchoProvider`, which returns a stub response instead of real generation. That is useful for CLI testing, but not for real use.

## Configuration

The CLI loads `.env` automatically when `python-dotenv` is available.

Common settings:

```bash
LILBOT_BACKEND=auto
LILBOT_MODEL_PATH=/path/to/model
LILBOT_DEVICE=auto
LILBOT_MAX_NEW_TOKENS=48
LILBOT_QUANTIZE_4BIT=1
LILBOT_DO_SAMPLE=0
LILBOT_STREAM=1
LILBOT_MAX_AGENT_STEPS=4
LILBOT_HISTORY_MESSAGES=8
LILBOT_SESSION_ID=default
LILBOT_LOG_LEVEL=WARNING
LILBOT_WORKSPACE_ROOT=/path/to/workspace
LILBOT_MEMORY_DB_PATH=/path/to/memory_store.db
LILBOT_MEMORY_JSON_PATH=/path/to/memory_store.json
```

What these mean:

- `LILBOT_BACKEND`
  - `auto`: use the local Hugging Face backend when a model path is available, otherwise use the echo backend
  - `hf`: require a local Hugging Face model path
  - `echo`: use the lightweight placeholder backend for CLI/testing flows
- `LILBOT_DEVICE`
  - `auto`: prefer CUDA if available
  - `cpu`: force CPU inference
  - `cuda`: require CUDA, fail if unavailable
- `LILBOT_MAX_NEW_TOKENS`
  - caps response length
  - lower is usually faster
- `LILBOT_QUANTIZE_4BIT`
  - enables 4-bit loading when CUDA and `bitsandbytes` are available
- `LILBOT_DO_SAMPLE`
  - `0` means greedy decoding, which is faster and more deterministic
  - `1` enables sampling
- `LILBOT_STREAM`
  - `1` enables safe direct-answer streaming in the CLI
  - `0` disables streaming and prints full answers only after each request completes
- `LILBOT_MAX_AGENT_STEPS`
  - maximum number of tool calls per request
- `LILBOT_HISTORY_MESSAGES`
  - number of recent messages loaded into the in-memory working context at startup
- `LILBOT_SESSION_ID`
  - default persistent session name
- `LILBOT_MEMORY_DB_PATH`
  - SQLite database path for notes and session history
- `LILBOT_MEMORY_JSON_PATH`
  - optional legacy JSON file path for one-time note import

## Starting Lilbot

Interactive mode:

```bash
python3 -m lilbot
```

Explicit interactive mode still works:

```bash
python3 -m lilbot run
```

One-shot prompt:

```bash
python3 -m lilbot --prompt "Summarize this repository"
```

One-shot prompt with explicit backend and streaming control:

```bash
python3 -m lilbot --backend hf --stream --prompt "Summarize this repository"
python3 -m lilbot --backend echo --no-stream --prompt "Hello"
```

Direct inline request without `--prompt`:

```bash
python3 -m lilbot "Summarize this repository"
```

Manual command as a direct request:

```bash
python3 -m lilbot ls
python3 -m lilbot read README.md
python3 -m lilbot notes groceries
```

Show help:

```bash
python3 -m lilbot --help
python3 -m lilbot help
```

## Bash `!` Gotcha

In interactive `bash`, `!` triggers shell history expansion.

This means this may fail:

```bash
python3 -m lilbot !ls
```

Use one of these instead:

```bash
python3 -m lilbot --prompt '!ls'
python3 -m lilbot ls
```

Inside the interactive `lilbot` prompt itself, `!ls` works normally.

## Prefix Commands

Prefix commands are the deterministic tool layer. They do not need the LLM.

### `!help`

Show the available built-in commands.

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

- paths outside the workspace root are rejected
- command-line shell flags like `-la` are ignored by the local command handler
- output is capped for very large directories

### `!read <file>`

Read a text file inside the workspace root.

Examples:

```bash
!read README.md
!read lilbot/cli/main.py
python3 -m lilbot read README.md
```

Notes:

- binary files are not dumped
- very large files are truncated
- paths outside the workspace root are rejected

### `!sys`

Show basic local system information.

Examples:

```bash
!sys
python3 -m lilbot sys
```

Typical output includes:

- OS
- Python version
- current directory
- CPU usage
- RAM usage

### `!note <text>`

Save a note to persistent memory.

Examples:

```bash
!note Buy oat milk
!note My preferred editor is Neovim
python3 -m lilbot note "Book dentist appointment"
```

Use notes for stable personal facts, tasks, preferences, and reminders.

### `!notes [query]`

List recent saved notes or search them.

Examples:

```bash
!notes
!notes milk
python3 -m lilbot notes groceries
```

If you omit the query, `lilbot` returns recent notes. If you include text, it ranks likely matches.

### `!history [query]`

List recent messages from the active session or search earlier conversation in that session.

Examples:

```bash
!history
!history memory
python3 -m lilbot --session-id work history roadmap
```

This is session-specific. If you switch `--session-id`, you switch to a different history thread.

## Using Agent Mode

Normal prompts go through the agent loop. This is where `lilbot` becomes more than a command launcher.

Examples:

```bash
python3 -m lilbot "Summarize the current CLI behavior from the README."
python3 -m lilbot "What notes do I have about groceries?"
python3 -m lilbot "What did we decide about memory last time?"
python3 -m lilbot "Read the main CLI file and explain how prompt parsing works."
```

What happens under the hood:

1. `lilbot` loads recent session messages for the chosen session
2. it retrieves relevant notes and relevant prior history for the current request
3. it builds an agent prompt with tool definitions
4. the model either answers directly or requests a tool
5. tool observations are fed back to the model
6. if the model misbehaves after a useful tool result, `lilbot` can fall back to the best observation it already has
7. the final answer is printed and persisted into session history

## What Tools the Agent Can Use

The current toolset is intentionally small:

- `list_files`
- `read_file`
- `system_info`
- `save_note`
- `search_notes`
- `search_history`

The agent is instructed to:

- prefer tools over guessing when local state matters
- prefer `search_notes` when the user may be asking about saved memory
- prefer `search_history` when the user asks about earlier conversation
- use `save_note` only when the user explicitly asks to remember or save something
- avoid inventing personal facts that are not supported by notes, history, or tool output
- summarize files instead of dumping raw contents when the request is a summary

## Notes and Memory

Lilbot stores memory in SQLite by default:

```text
lilbot/memory/memory_store.db
```

The database currently stores:

- notes
- session messages
- small metadata entries, such as legacy import markers

### Legacy JSON Import

If `lilbot/memory/memory_store.json` exists, notes from that file are imported automatically the first time the SQLite store is opened.

The JSON file is not deleted automatically. It remains as a legacy artifact unless you remove it yourself.

### Good Uses for Notes

Use notes for information like:

- shopping lists
- recurring tasks
- personal preferences
- project decisions you want to keep beyond one session
- reminders that should survive across sessions

Examples:

```bash
!note I prefer concise answers.
!note Project alpha uses SQLite for memory.
!note Pick up coffee beans on Friday.
```

Then later:

```bash
!notes coffee
python3 -m lilbot "What do I need to buy?"
```

## Sessions

Sessions are one of the most useful features for personal agent workflows.

Examples:

```bash
python3 -m lilbot --session-id work
python3 -m lilbot --session-id personal
python3 -m lilbot --session-id repo-review
```

Recommended usage:

- keep one session per major project
- use a separate personal session for reminders and life admin
- keep experimental prompts in a throwaway session

Session history is automatically saved after successful LLM turns. Manual `!` commands are not stored as session exchanges unless they are part of a normal agent turn.

## Performance and Latency

If `lilbot` feels slow, the biggest factor is usually the model runtime, not the CLI logic.

### Highest-Impact Ways to Speed It Up

- use a smaller model
- get CUDA working
- enable 4-bit quantization when supported
- keep `--max-new-tokens` low
- leave sampling disabled unless you need it
- leave streaming enabled so direct answers appear sooner

### Recommended Faster Settings

```bash
python3 -m lilbot \
  --device auto \
  --quantize-4bit \
  --max-new-tokens 48 \
  --no-sample \
  "Summarize the README"
```

### CPU Warning

If the model runs on CPU, latency will be much higher. The provider already warns about that.

### Partial Offload Warning

If the model is partly offloaded to CPU or disk, responses can still be slow even when CUDA is technically available.

### Large Outputs

Long prompts and long requested answers both increase latency. If you want a snappier assistant, ask narrower questions and keep response budgets short.

## Troubleshooting

### The assistant says it is using an echo provider

Cause:

- no local model path was found

Fix:

- set `LILBOT_MODEL_PATH`
- or place a supported model under `lilbot/models/falcon3_10b_instruct`

### Startup says `transformers` is too old

Cause:

- installed `transformers` is older than what your model needs

Fix:

```bash
pip install -U -r requirements.txt
```

### GPU is available but quantization is not used

Possible causes:

- `bitsandbytes` is missing
- CUDA is unavailable to PyTorch
- `--device cpu` was set

Fix:

```bash
pip install bitsandbytes
python3 -m lilbot --device auto --quantize-4bit "test prompt"
```

### Generation runs out of GPU memory

Try one or more of:

- lower `--max-new-tokens`
- disable `--quantize-4bit` if the quantized path is unstable on your setup
- use `--device cpu`
- use a smaller model

### `!ls` or `!read` says the path is outside the workspace root

Cause:

- the path resolves outside the allowed workspace

Fix:

- start `lilbot` from the right directory
- or set `LILBOT_WORKSPACE_ROOT`

### `!history` shows nothing

Possible causes:

- you are in a new session ID
- there were no successful LLM turns stored yet
- you are searching for text that does not match earlier messages

Try:

```bash
python3 -m lilbot --session-id default history
```

### The model keeps repeating tool calls or prints weird protocol text

Lilbot now blocks repeated identical tool calls and strips common malformed role labels such as `[assistant] TOOL: ...`, but small local models can still be brittle.

If this still happens often:

- lower task complexity
- ask narrower questions
- prefer direct `!` commands for deterministic retrieval
- use a stronger or better-instruct local model

### Bash rejects `!` commands on the command line

Use quoted `--prompt` input or omit `!` entirely on the shell command line:

```bash
python3 -m lilbot --prompt '!notes'
python3 -m lilbot notes
```

### The model guesses personal facts incorrectly

Recent agent updates push `lilbot` to rely on notes, history, and tool observations before answering things like your name or other personal facts.

If you want those answers to be reliable:

- save them explicitly with `!note`
- keep related discussion in the same `--session-id`
- ask `!notes` or `!history` directly if you want deterministic retrieval

## Example Workflows

### Workflow 1: Personal Notes Assistant

```bash
python3 -m lilbot --session-id personal
```

Inside the CLI:

```text
!note Buy coffee filters
!note I prefer concise answers
What do I need to buy soon?
What communication style do I prefer?
```

### Workflow 2: Repo Assistant

```bash
python3 -m lilbot --session-id lilbot-dev
```

Prompts:

```text
Read the README and summarize the user-facing features.
What did we decide earlier about memory storage?
List the main CLI arguments and explain when to use each one.
```

### Workflow 3: Workspace Inspection

```bash
python3 -m lilbot --session-id debug
```

Prompts:

```text
Read lilbot/cli/main.py and explain how one-shot prompt parsing works.
Inspect the tools and tell me which ones are safe to expose to the model.
```

## File Map

If you are developing `lilbot`, these are the key files:

- `lilbot/cli/main.py`
  - CLI parsing
  - interactive loop
  - one-shot handling
  - session loading and persistence
- `lilbot/cli/agent.py`
  - agent loop
  - prompt construction
  - response parsing
  - tool protocol
- `lilbot/llm/provider.py`
  - local Hugging Face model loading
  - quantization handling
  - inference settings
  - runtime warnings
- `lilbot/tools/filesystem.py`
  - safe file listing and reading
- `lilbot/tools/notes.py`
  - note save and retrieval
- `lilbot/tools/history.py`
  - session history retrieval
- `lilbot/memory/memory.py`
  - SQLite-backed notes and session storage

## Extending Lilbot

The current codebase is intentionally simple. Adding a new tool is straightforward.

General pattern:

1. implement the function in a `lilbot/tools/*.py` module
2. add a tool definition with `name`, `description`, `parameters`, `example`, and `execute`
3. register it through `lilbot/tools/__init__.py`
4. optionally add a manual `!` command in `lilbot/cli/main.py`
5. update docs

If you add a new backend, keep it behind the provider factory in `lilbot/llm/provider.py` so the CLI does not need backend-specific branching.

When adding tools that can modify files or run shell commands, keep the current safety posture:

- default to read-only where possible
- require explicit user intent for writes
- keep workspace boundaries clear
- provide deterministic error messages

## Current Limits

`lilbot` is becoming a useful local agent, but there are still clear limits:

- no streaming token output yet
- limited toolset
- no explicit human approval flow for risky future tools
- no advanced retrieval ranking beyond simple text heuristics
- performance is still tied heavily to your local model/runtime choice

## Recommended Next Improvements

If you want to keep pushing `lilbot` toward a stronger personal agent, the highest-value next steps are:

- add streaming output
- support a faster local backend such as `llama.cpp`
- add better retrieval and memory ranking
- add safe shell and editing tools with confirmation
- add automated tests for agent loops, memory retrieval, and CLI parsing

The first and last items are now partially in place: lilbot has direct-answer streaming and a lightweight `unittest` regression suite. The biggest remaining production jump is a faster backend plus stronger retrieval and tool control.

## Running Tests

Run the lightweight regression suite:

```bash
python -m unittest discover -s tests -v
```

## Short Command Reference

```bash
python3 -m lilbot
python3 -m lilbot --prompt "Hello"
python3 -m lilbot "Summarize this repo"
python3 -m lilbot help
python3 -m lilbot ls
python3 -m lilbot read README.md
python3 -m lilbot notes
python3 -m lilbot history
python3 -m lilbot --session-id work "What did we decide earlier?"
```
