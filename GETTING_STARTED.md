# Getting Started

This is a short, safe path to run the project locally.

## 1) Create environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Configure
```bash
cp .env.example .env
```

Edit `.env` and set required keys:
- `API_KEY`, `API_SECRET`, `ACCESS_TOKEN`, `ACCESS_TOKEN_SECRET`, `BEARER_TOKEN`
- `BOT_USER_ID`

Optional:
- `TEXT_MODEL_PATH`, `SD_MODEL_PATH`
- `BOT_NAME`, `BOT_HANDLE`, `BOT_BRAND`, `BOT_TOPICS`
- `ENABLE_NEWS`, `ENABLE_MEMES`
- `BOT_CONFIG` (YAML file for persona + behavior)
- `BOT_PROMPTS` (YAML file for prompts)

You can start from the generic example config:
- `examples/local_llm/.env.example`
- `examples/local_llm/bot.yml`

## 3) Run simulation (safe)
```bash
python src/sim-main.py
```

## 4) Run live
```bash
python src/main.py
```

## Troubleshooting
- If CUDA is missing, the model load will fail. Install proper GPU drivers + CUDA.
- If you see crypto news, set `ENABLE_NEWS=0`.
- If you have no memes, set `ENABLE_MEMES=0`.

## Security
See `SANITIZED_ENV.md` for safe handling of secrets.
