# Getting Started

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
LILBOT_MODEL_PATH=/path/to/model
LILBOT_DEVICE=auto
LILBOT_MAX_NEW_TOKENS=48
LILBOT_QUANTIZE_4BIT=1
LILBOT_DO_SAMPLE=0
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
```

## 5. Ask the model a prompt
```bash
python3 -m lilbot --prompt "Summarize this project."
```
