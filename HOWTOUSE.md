# How To Use Lilbot

Lilbot is intentionally small. Treat it as a local agent scaffold, not a product with domain-specific workflows.

## Mental Model

There are three layers:

1. Direct CLI commands like `tools`, `models`, and `doctor`
2. Deterministic `!` commands in chat for workspace/system access
3. A model-backed agent loop for everything else

## Commands

Start chat:

```bash
python -m lilbot
```

Run one prompt:

```bash
python -m lilbot run "summarize the README"
```

Inspect the runtime:

```bash
python -m lilbot tools
python -m lilbot models
python -m lilbot doctor
```

## Built-In Chat Commands

```text
!help
!tools
!ls [path]
!read <file>
!write <file> <text>
!append <file> <text>
!sys
```

## Model Expectations

Lilbot uses a narrow tool protocol:

```text
FINAL: <answer>
TOOL: <tool_name> <json object>
```

That makes it easy to swap prompts, test fake models, or replace the provider layer.

## Workspace Rules

- File tools stay inside `LILBOT_WORKSPACE_ROOT`.
- If `LILBOT_WORKSPACE_ROOT` is not set, Lilbot uses the current working directory.
- Session history is local-only and stored under the app data directory.

## Recommended Files To Read

- `lilbot/cli/main.py`
- `lilbot/cli/agent.py`
- `lilbot/llm/provider.py`
- `lilbot/core/session_store.py`
- `lilbot/tools/filesystem.py`
