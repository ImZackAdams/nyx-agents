# Getting Started

Need the complete guide after this quick start? Read [HOWTOUSE.md](HOWTOUSE.md).

## 1. Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install `bitsandbytes` separately if you want 4-bit GPU quantization.

## 2. Configure the model
You can use `.env` or exported environment variables:
```bash
LILBOT_BACKEND=auto
LILBOT_MODEL_PATH=/path/to/model
LILBOT_DEVICE=auto
LILBOT_MAX_NEW_TOKENS=48
LILBOT_QUANTIZE_4BIT=1
LILBOT_DO_SAMPLE=0
LILBOT_STREAM=1
LILBOT_SESSION_ID=default
```

If `lilbot/models/falcon3_10b_instruct` exists, `lilbot` will use it automatically.

## 3. Start the CLI
```bash
python3 -m lilbot
```

## 4. Try a one-shot command
```bash
python3 -m lilbot --prompt "!sys"
python3 -m lilbot --prompt "!read README.md"
python3 -m lilbot --prompt "!notes"
python3 -m lilbot --prompt "!history"
```

## 5. Ask the model a prompt
```bash
python3 -m lilbot --prompt "Summarize this project."
```

The model can now use local tools automatically for normal prompts, so queries like `What notes do I have about groceries?` or `Read the README and summarize it.` can trigger note lookup or file reads before the final answer.

Session history is stored persistently in SQLite alongside notes. Use `--session-id project-a` if you want a separate conversation thread, and use `!history [query]` to inspect or search what was said earlier in that session.

Run the lightweight regression tests with:

```bash
python -m unittest discover -s tests -v
```
