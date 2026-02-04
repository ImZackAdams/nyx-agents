# Local LLM Example

This is a generic, local-first example configuration intended for a hackable bot prototype.

## Files
- `.env.example`: environment variables for identity, credentials, and model paths
- `bot.yml`: persona + behavior + prompts in one file

## Usage
1. Copy `examples/local_llm/.env.example` to `.env` at repo root.
2. Update required keys and model paths.
3. Run `python src/sim-main.py` for a safe local test.
