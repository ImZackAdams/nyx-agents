# NyxAgents Example Config

This folder contains the original branded persona configuration.

## Quick Use
1. From repo root, copy the example env.

```bash
cp examples/nyxagents/.env.example .env
```

2. Update Twitter/X credentials and `BOT_USER_ID` in `.env`.
3. Run the simulator or live bot.

```bash
python src/sim-main.py
python src/main.py
```

## Files
- `.env.example`: environment variables for identity, credentials, and model paths
- `bot.yml`: persona + behavior + prompts
- `prompts.yml`: prompt config used by `BOT_PROMPTS` (optional)
