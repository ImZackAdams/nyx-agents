# Lilbot

`lilbot` is a minimal local LLM and agent framework for the terminal.

It keeps only the core pieces:

- a CLI chat interface
- a local model provider layer
- a small agent loop with tool calling
- lightweight session history
- a few workspace-safe built-in tools

## Core Components

- `lilbot/cli/main.py`
  The terminal interface. Handles `chat`, one-shot prompts, model inspection, doctor output, and direct `!` commands.
- `lilbot/cli/agent.py`
  The generic agent loop. The model must answer with `FINAL:` or `TOOL:`.
- `lilbot/llm/provider.py`
  Provider abstraction plus the local Hugging Face backend.
- `lilbot/core/session_store.py`
  JSONL-backed chat history.
- `lilbot/tools/`
  Built-in tools for listing files, reading files, writing files, and getting basic system info.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m lilbot doctor
python -m lilbot tools
python -m lilbot
```

For local model support:

```bash
pip install -e ".[hf]"
export LILBOT_MODEL_PATH=/path/to/local/model
python -m lilbot models
```

Optional 4-bit GPU support:

```bash
pip install -e ".[hf,quantization]"
```

## CLI Surface

Interactive chat:

```bash
python -m lilbot
```

One-shot prompt:

```bash
python -m lilbot run "summarize this repository"
```

Inline prompt:

```bash
python -m lilbot "summarize the README"
```

Utility commands:

```bash
python -m lilbot tools
python -m lilbot models
python -m lilbot doctor
```

## Chat Commands

These run without a model:

```text
!help
!tools
!ls [path]
!read <file>
!write <file> <text>
!append <file> <text>
!sys
```

Filesystem tools are restricted to `LILBOT_WORKSPACE_ROOT` or the current working directory.

## Agent Protocol

The runtime expects the model to respond with exactly one of these forms:

```text
FINAL: <answer>
TOOL: <tool_name> <json object>
```

Built-in tools:

- `list_files`
- `read_file`
- `write_file`
- `system_info`

## Session History

Lilbot stores chat history locally as JSONL under its app-data directory. Use `--session-id` to keep separate conversations.

## Tests

```bash
python -m unittest discover -s tests -v
```
