# NyxAgents Example Config

This folder contains a branded configuration example for the NyxAgents persona.

## Files
- `.env.example`: environment variables for identity, credentials, and model paths.
- `persona.yml`: reference persona values (not currently auto-loaded).
- `bot.yml`: persona + behavior config used by `BOT_CONFIG`.
- `prompts.yml`: prompt config used by `BOT_PROMPTS` (or embedded in `bot.yml`).

## Usage
1. Copy `.env.example` to `.env` in the repo root.
2. Fill in Twitter/X credentials and `BOT_USER_ID`.
3. Run the simulator or bot.
