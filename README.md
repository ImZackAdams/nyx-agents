# Lilbot

`lilbot` is a small local-LLM CLI with a few built-in `!` commands for common workstation tasks.

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

Filesystem commands are limited to the workspace root used when you start the CLI. Override that root with `LILBOT_WORKSPACE_ROOT=/path/to/workspace` if needed.
In interactive `bash`, quote `!` commands like `python3 -m lilbot --prompt '!ls'`, or omit `!` on the command line and use `python3 -m lilbot ls`.

## Configuration
`lilbot` loads `.env` automatically when `python-dotenv` is installed.

Common environment variables:
```bash
LILBOT_MODEL_PATH=/path/to/model
LILBOT_DEVICE=auto
LILBOT_MAX_NEW_TOKENS=48
LILBOT_QUANTIZE_4BIT=1
LILBOT_DO_SAMPLE=0
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

## License
MIT. See `LICENSE`.
