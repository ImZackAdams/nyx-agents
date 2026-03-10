# Contributing

Thanks for helping improve this project. This repo is an OSS MVP, so clarity and small, focused changes are best.

## How to Contribute
1. Fork the repo and create a branch.
2. Keep changes scoped to one concern.
3. Add notes in your PR description about how to test.

## Development Notes
- Use `python -m lilbot --prompt "!sys"` or other prefix commands for lightweight smoke tests.
- Avoid introducing new dependencies unless required.
- Keep persona and brand specifics out of core logic.

## Code Style
- Prefer clear, explicit code over cleverness.
- Avoid nested logic when a helper function makes intent clearer.

## Reporting Issues
- Include steps to reproduce.
- Include OS, Python version, and GPU/driver info if relevant.
