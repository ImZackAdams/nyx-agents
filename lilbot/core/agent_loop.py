"""Compatibility wrapper for the existing lilbot agent loop."""

from __future__ import annotations

from lilbot.cli.agent import maybe_answer_without_llm, run_agent

__all__ = [
    "maybe_answer_without_llm",
    "run_agent",
]
