# Roadmap

Lilbot is now scoped as a small local LLM/agent skeleton.

## Near Term

- add an Ollama or llama.cpp provider alongside the Hugging Face backend
- support richer structured tool schemas
- improve streaming and interruption handling for longer generations
- add cleaner session inspection and reset commands

## Direction

- keep the runtime local-first
- keep the tool protocol narrow and testable
- keep the CLI easy to understand from the source tree
- add features only when they strengthen the framework core

## Out Of Scope

- product-specific workflow layers
- remote SaaS dependencies by default
- background automation
- broad shell execution by default
