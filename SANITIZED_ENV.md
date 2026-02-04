# Sanitized Environment Guide

This project uses many secrets (API keys, tokens, private keys). Never share or commit them.

## What to Do If Secrets Were Exposed
1. Rotate/revoke the exposed keys immediately.
2. Generate new credentials in each provider dashboard.
3. Update your local `.env` with the new values.
4. If any secrets were committed to git history, remove them and rotate again.

## Recommended Rotation Checklist
- Twitter/X: API key, API secret, bearer token, access token, access token secret
- Solana: private key
- Pinata: API key, API secret, JWT
- Helius: API key
- Any other service tokens in `.env`

## Safe Sharing
- Share only `.env.example` or a redacted `.env` with values removed.
- Avoid pasting secrets into chat or issue trackers.

## Redaction Template
When sharing configs for debugging, replace values like this:

```
API_KEY=***
API_SECRET=***
BEARER_TOKEN=***
ACCESS_TOKEN=***
ACCESS_TOKEN_SECRET=***
```
