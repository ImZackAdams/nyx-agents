# Roadmap

This project is intentionally small. The roadmap is about making Lilbot easier to trust, easier to try, and more useful without turning it into a fully autonomous coding agent.

## Near Term

- publish a lightweight package install story that does not force local-model dependencies
- add import, export, and reset commands for notes and profile memory
- improve `doctor` with model-path validation details and clearer remediation steps
- document a recommended small-model setup for CPU-only and GPU-backed users
- add GitHub issue templates, CI, and a short release checklist

## Product Direction

- keep deterministic workspace inspection strong
- keep memory local and understandable
- add capabilities only when the safety boundary stays obvious
- prefer transparent, testable tool use over broad hidden autonomy

## Explicitly Out Of Scope For Now

- web browsing
- arbitrary shell execution
- long-horizon autonomous planning
- silent background actions
