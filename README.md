# NyxAgent Bot Framework (OSS MVP)

A lightweight, configurable Twitter/X bot framework for generating text, posting memes, summarizing RSS news, and replying to mentions (optionally with image generation).

This repository is an OSS MVP: simple to run locally, clear extension points, and easy to rebrand for your own persona.

## Features
- Text tweet generation using a local LLM (Falcon).
- RSS news ingestion and summarization.
- Meme posting from a local folder.
- Reply handling for mentions.
- Optional image replies via Stable Diffusion.
- Simulation runner for safe local testing.

## Quickstart
1. Create a virtual environment and install dependencies.
2. Copy `.env.example` to `.env` and fill required values.
3. Run the simulator or the main bot.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Simulation (no real posts):
```bash
python src/sim-main.py
```

Live bot:
```bash
python src/main.py
```

## Configuration
All configuration is via environment variables. See `.env.example`.

Required:
- `API_KEY`, `API_SECRET`, `ACCESS_TOKEN`, `ACCESS_TOKEN_SECRET`, `BEARER_TOKEN` (or `TWITTER_*` equivalents).
- `BOT_USER_ID` for reply handling.

Optional identity overrides:
- `BOT_NAME`
- `BOT_HANDLE`
- `BOT_BRAND`
- `BOT_TOPICS`

Optional model overrides:
- `TEXT_MODEL_PATH`
- `SD_MODEL_PATH`

## Repo Layout
- `src/main.py`: production bot entrypoint.
- `src/sim-main.py`: simulation entrypoint.
- `src/bot/`: bot logic, posting, replies.
- `src/config/`: personality and posting configuration.
- `src/bot/news/`: RSS ingestion and content extraction.
- `src/utils/`: text cleaning, logging, monitoring.

## Notes
- GPU and CUDA are required for the Falcon model and Stable Diffusion.
- The RSS sources are crypto-centric by default. Customize in `src/bot/news/news_service.py`.

## License
MIT. See `LICENSE`.
