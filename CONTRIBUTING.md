# Contributing

Thanks for helping improve this project. Clarity, small focused changes, and visible user impact matter more than cleverness.

## How to Contribute
1. Fork the repo and create a branch.
2. Keep changes scoped to one concern.
3. Add notes in your PR description about how to test.

## Development Notes
- Use `python -m lilbot doctor` and `python -m lilbot --prompt "!sys"` for lightweight smoke tests.
- Prefer `pip install -e .` for the base CLI and `pip install -e ".[hf]"` only when you need local-model support.
- Avoid introducing new dependencies unless required.
- Keep persona and brand specifics out of core logic.

## Code Style
- Prefer clear, explicit code over cleverness.
- Avoid nested logic when a helper function makes intent clearer.

## Reporting Issues
- Include steps to reproduce.
- Include OS, Python version, and GPU/driver info if relevant.
