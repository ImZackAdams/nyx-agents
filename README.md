# Local LLM Bot Framework

A local-first, customizable Twitter/X bot framework for prototyping with local LLMs. It can run in a fully offline simulation mode (no GPU, no credentials) or as a live bot with CUDA-based text generation and optional image replies.

## What This Does
- Generates tweets using a local text model and a configurable persona.
- Posts on a schedule, with optional news summaries and memes.
- Monitors replies and responds with text or images.
- Supports simulation mode for fast iteration without real Twitter calls.

## Quick Start (Prototype, No GPU)
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

This mode does not require GPU, model downloads, or Twitter credentials.

## Full Local LLM Mode (GPU)
1. Install full dependencies.

```bash
pip install -r requirements.txt
```

2. Set model paths in `.env`.

```bash
TEXT_MODEL_PATH=/path/to/your/text/model
SD_MODEL_PATH=/path/to/your/sd/model
```

3. Disable dry run and enable the image pipeline.

```bash
DRY_RUN=0
SKIP_IMAGE_PIPELINE=0
```

4. Run the simulator or live bot.

```bash
python src/sim-main.py
python src/main.py
```

## Configuration
All customization is done through `.env` and optional YAML.

Recommended config:
- `examples/local_llm/bot.yml`
- Set `BOT_CONFIG=examples/local_llm/bot.yml`

Prompt overrides:
- `BOT_PROMPTS=examples/local_llm/prompts.yml`

### Required For Live Posting
- Twitter/X credentials: `API_KEY`, `API_SECRET`, `ACCESS_TOKEN`, `ACCESS_TOKEN_SECRET`, `BEARER_TOKEN`
- `BOT_USER_ID` for reply handling

### Feature Toggles
- `ENABLE_NEWS` and `NEWS_FEEDS` for RSS-driven posts
- `ENABLE_MEMES` to post from a local memes folder
- `DRY_RUN` to skip model loading
- `SKIP_IMAGE_PIPELINE` to skip Stable Diffusion
- `SKIP_TWITTER_VALIDATION` for sim mode

## Architecture (At A Glance)
- `src/main.py`: production bot entrypoint
- `src/sim-main.py`: simulation entrypoint
- `src/bot/main_bot.py`: personality bot and model usage
- `src/bot/posting/`: tweet generation, meme posting, reply handling
- `src/bot/news/`: RSS ingestion and content extraction
- `src/api/twitter/`: Twitter client wrappers
- `src/config/`: persona, posting, and model configuration
- `examples/`: example configs and prompts

## How Posting Works
- A random roll decides between news, meme, or text post.
- News posts summarize RSS articles into a short tweet.
- Text posts use the persona prompt + prompt libraries.
- All tweets are cleaned and length-validated before posting.

## Reply Handling
- Replies are polled on a schedule after posting.
- Each conversation keeps a short history for context.
- If a reply explicitly requests an image, the bot generates one (when the image pipeline is enabled).

## News Ingestion
- Uses RSS feeds from `NEWS_FEEDS`.
- Extracts article content via a headless browser + HTML parsing.
- Tracks posted articles in `posted_articles.json` to avoid duplicates.

## Memes
- Images are pulled from a local `memes/` folder in the repo root.
- Captions are defined in `src/bot/prompts.py`.

## Tips And Troubleshooting
- If the model fails to load, confirm `TEXT_MODEL_PATH` exists and contains required files.
- If posting fails, verify credentials and ensure `DRY_RUN=0`.
- If the bot won’t reply, check `BOT_USER_ID` and `SKIP_TWITTER_VALIDATION`.
- If image generation fails, ensure `SD_MODEL_PATH` is valid and CUDA is available.

## Safety And Secrets
- Never commit `.env` files or credentials.
- See `SANITIZED_ENV.md` for safe handling of secrets.
- See `GETTING_STARTED.md` for a concise walkthrough.

## License
MIT. See `LICENSE`.
