# Lilbot

`lilbot` is a small local-LLM CLI that is growing into a practical local agent. It combines direct `!` commands, persistent memory, and an agent loop that can use local tools before answering.

For the full usage guide, workflows, troubleshooting, and extension notes, see [HOWTOUSE.md](HOWTOUSE.md).

## Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional extras:
```bash
pip install bitsandbytes
```

## Run
Interactive mode:
```bash
python3 -m lilbot
```

One-shot prompt:
```bash
python3 -m lilbot --prompt "Hello"
```

`lilbot run` still works if you prefer the explicit form.

You can also pass a direct one-shot request without `--prompt`:
```bash
python3 -m lilbot help
python3 -m lilbot ls
python3 -m lilbot "Summarize this project"
```

## Prefix Commands
Inside the CLI, or through `--prompt`, you can run:

- `!help`
- `!ls [path]`
- `!read <file>`
- `!sys`
- `!note <text>`
- `!notes [query]`
- `!history [query]`

Filesystem commands are limited to the workspace root used when you start the CLI. Override that root with `LILBOT_WORKSPACE_ROOT=/path/to/workspace` if needed.
In interactive `bash`, quote `!` commands like `python3 -m lilbot --prompt '!ls'`, or omit `!` on the command line and use `python3 -m lilbot ls`.

## Agent Mode
Normal prompts now run through an agent loop. The LLM can choose to call local tools such as file reads, note search, session-history search, or system inspection before returning a final answer.

Examples:
```bash
python3 -m lilbot "What notes do I have about groceries?"
python3 -m lilbot "Read the README and summarize the current CLI behavior."
python3 -m lilbot "Based on my notes, what should I buy?"
python3 -m lilbot "What did we decide about memory last time?"
```

The CLI prints tool calls to stderr as they happen so you can see what the agent is doing.
The agent can save notes too, but it only does that when you explicitly ask it to remember or save something.
Conversation history is stored persistently, so the agent can retrieve earlier messages from the current session when relevant.
The agent now has a few defensive behaviors too: repeated identical tool calls are blocked, malformed protocol output is normalized, file/listing summary requests fall back to deterministic summaries when the model gets sloppy, and personal-fact questions only answer from notes/history instead of guessing.

## Configuration
`lilbot` loads `.env` automatically when `python-dotenv` is installed.

Common environment variables:
```bash
LILBOT_MODEL_PATH=/path/to/model
LILBOT_DEVICE=auto
LILBOT_MAX_NEW_TOKENS=48
LILBOT_QUANTIZE_4BIT=1
LILBOT_DO_SAMPLE=0
LILBOT_MAX_AGENT_STEPS=4
LILBOT_HISTORY_MESSAGES=8
LILBOT_SESSION_ID=default
LILBOT_LOG_LEVEL=WARNING
LILBOT_WORKSPACE_ROOT=/path/to/workspace
LILBOT_MEMORY_DB_PATH=/path/to/memory_store.db
```

Notes:
- The default model path is `lilbot/models/falcon3_10b_instruct` when that directory exists.
- The default response budget is intentionally shorter now to reduce latency for local use. Raise `--max-new-tokens` when you want longer replies.
- Greedy decoding is the default because it is faster and more predictable than sampling for CLI use. Re-enable sampling with `--sample`.
- `--quantize-4bit` only applies when CUDA and `bitsandbytes` are available.
- Use `--device cpu` on CPU-only machines or when GPU memory is too tight.
- Notes are now stored in SQLite by default at `lilbot/memory/memory_store.db`. Existing `memory_store.json` notes are imported automatically the first time the new store is opened.
- Session history is stored in the same SQLite database. Use `--session-id work` or `LILBOT_SESSION_ID=work` to keep separate long-running conversations.
- `!history` shows recent conversation for the active session. `!history memory` searches earlier messages in that session.
- `LILBOT_MAX_AGENT_STEPS` limits how many tool calls the model can make before the request is stopped.

## License
MIT. See `LICENSE`.
