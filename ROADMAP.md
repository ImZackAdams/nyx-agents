# Lilbot Roadmap

Lilbot is already usable as a local AI CLI, but the next phase is about making it easier to install, easier to trust, and easier to extend.

## Current Focus

- guided setup with `lilbot init`
- environment diagnostics with `lilbot doctor`
- one-command validation with `lilbot self-test`
- persistent per-user config
- interactive slash commands
- clearer onboarding docs

## Near Term

- package and publish clean install paths for `pipx`, `venv`, and `conda`
- improve model-load error messages with more actionable fix suggestions
- add clearer progress output during long model loads and tool runs
- expand REPL quality-of-life features like command history and better interrupt handling

## Model and Runtime

- support additional local backends behind the existing model abstraction
- improve model auto-detection and hardware-based recommendations
- add warm-start and caching strategies to reduce cold-start latency
- expose better runtime telemetry for load time, generation time, and tool execution time

## Tooling

- deepen repository inspection tools
- add better stack-trace and error-log workflows
- improve system diagnostics beyond the current snapshot tools
- add safer write-assisted workflows behind explicit confirmation paths

## Retrieval

- repo chunking for larger codebases
- semantic retrieval over source files and logs
- lightweight indexing that stays local and opt-in

## UX and Documentation

- add an asciinema or demo GIF
- publish hardware-specific setup guides
- add a troubleshooting matrix by symptom
- improve the quickstart for first-time Linux users

## Longer Term

- richer session memory for a single working conversation
- workspace-aware profiles
- stronger plugin conventions for third-party tools
- better support for operating outside the current repository root
