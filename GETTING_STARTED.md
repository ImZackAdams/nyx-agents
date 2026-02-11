# Getting Started

This guide is optimized for a fast setup from a GitHub clone.

## Path A: Prototype (fast, no GPU)
1. Create a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install minimal dependencies.

```bash
pip install -r requirements-prototype.txt
```

3. Use the local example config.

```bash
cp examples/local_llm/.env.example .env
```

4. Run the simulator.

```bash
python src/sim-main.py
```

This mode uses `DRY_RUN=1` and does not require model downloads or Twitter credentials.

## Path B: Full Local LLM (GPU)
1. Install full dependencies.

```bash
pip install -r requirements.txt
```

2. Set model paths in `.env`.

```
TEXT_MODEL_PATH=/path/to/your/text/model
SD_MODEL_PATH=/path/to/your/sd/model
```

Note: model files are not included in this repo (too large for GitHub). Download them separately and point the paths above at your local folders.

### Where to get models
- Use any local text generation model that matches your GPU + VRAM budget.
- For images, use a local Stable Diffusion model folder.
- After download, set `TEXT_MODEL_PATH` and `SD_MODEL_PATH` to the local directories that contain the model files (not a single file).

3. Disable dry run.

```
DRY_RUN=0
SKIP_IMAGE_PIPELINE=0
```

4. Run the simulator or live bot.

```bash
python src/sim-main.py
python src/main.py
```

## Live Posting Requirements
Set these in `.env` to post to Twitter/X:
- `API_KEY`, `API_SECRET`, `ACCESS_TOKEN`, `ACCESS_TOKEN_SECRET`, `BEARER_TOKEN`
- `BOT_USER_ID`

## Customization
Use `BOT_CONFIG` and `BOT_PROMPTS` to customize persona and prompts.
- Example: `examples/local_llm/bot.yml`

## Troubleshooting
- If you want news, set `NEWS_FEEDS` to RSS URLs.
- If you have no memes, set `ENABLE_MEMES=0`.

## Security
See `SANITIZED_ENV.md` for safe handling of secrets.
Never commit `.env` to GitHub.
