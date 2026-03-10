#!/usr/bin/env bash
set -euo pipefail

if [ ! -d .venv ]; then
  python -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Fill in required values before running."
fi

echo "Setup complete. Run: python -m lilbot"
