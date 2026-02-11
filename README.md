# Local LLM Bot Framework (Prototype)

A local-first, customizable Twitter/X bot framework for prototyping with local LLMs.

This repo is designed to be easy to clone and run. Start with the prototype path, then upgrade to full local LLM mode.

## Start Here (Prototype, no GPU)
1. Clone the repo.

```bash
git clone <your-repo-url>
cd NyxAgent
```

2. Create a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install prototype dependencies.

```bash
pip install -r requirements-prototype.txt
```

4. Use the local example config.

```bash
cp examples/local_llm/.env.example .env
```

5. Run the simulator.

```bash
python src/sim-main.py
```

This path does not require GPU, model downloads, or Twitter credentials.

## Full Local LLM Mode (GPU)
1. Install full dependencies.

```bash
pip install -r requirements.txt
```

2. Set model paths in `.env`.

```
TEXT_MODEL_PATH=/path/to/your/text/model
SD_MODEL_PATH=/path/to/your/sd/model
```

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

## Customize
All customization is done through `.env` and YAML.

Recommended path:
- `examples/local_llm/bot.yml`
- `BOT_CONFIG=examples/local_llm/bot.yml`

Prompt overrides:
- `BOT_PROMPTS=examples/local_llm/prompts.yml`

## Configuration Quick Reference
Required for live posting:
- `API_KEY`, `API_SECRET`, `ACCESS_TOKEN`, `ACCESS_TOKEN_SECRET`, `BEARER_TOKEN`
- `BOT_USER_ID`

Common toggles:
- `ENABLE_NEWS`
- `ENABLE_MEMES`
- `NEWS_FEEDS` (comma-separated RSS URLs)

Prototype toggles:
- `DRY_RUN`
- `SKIP_IMAGE_PIPELINE`
- `SKIP_TWITTER_VALIDATION`

## Repo Layout
- `src/main.py`: production bot entrypoint
- `src/sim-main.py`: simulation entrypoint
- `src/bot/`: bot logic, posting, replies
- `src/config/`: personality and posting configuration
- `src/bot/news/`: RSS ingestion and content extraction
- `src/utils/`: text cleaning, logging, monitoring
- `examples/`: example configs

## Notes
- News is opt-in: set `NEWS_FEEDS` to enable.
- Never commit `.env` to GitHub.
- Model files are not included in this repo (too large for GitHub). Download them separately and set `TEXT_MODEL_PATH` / `SD_MODEL_PATH` in `.env`.
- See `SANITIZED_ENV.md` for safe handling of secrets.
- See `GETTING_STARTED.md` for a concise walkthrough.

## Model Downloads
- Use any local text generation model that fits your GPU + VRAM budget.
- For images, use a local Stable Diffusion model folder.
- Point `TEXT_MODEL_PATH` and `SD_MODEL_PATH` at directories that contain the model files.

## Example Configs
- `examples/local_llm/` for a generic local-first setup
- `examples/nyxagents/` for the original branded persona

## License
MIT. See `LICENSE`.
