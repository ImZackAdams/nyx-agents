"""High-level Lilbot agent orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from lilbot.controller import LilbotController
from lilbot.memory.session import LilbotSession
from lilbot.model.base import BaseModel
from lilbot.tools.registry import ToolRegistry
from lilbot.utils.logging import StepLogger


@dataclass(frozen=True)
class AgentResult:
    """A completed Lilbot run."""

    answer: str
    session: LilbotSession

    @property
    def steps(self) -> int:
        return len(self.session.steps)


class LilbotAgent:
    """Small wrapper that binds a model, controller, and per-run session."""

    def __init__(
        self,
        model: BaseModel,
        tool_registry: ToolRegistry,
        *,
        max_steps: int = 4,
        logger: StepLogger | None = None,
    ) -> None:
        self.controller = LilbotController(
            model=model,
            tool_registry=tool_registry,
            max_steps=max_steps,
            logger=logger,
        )

    def answer(self, request: str, *, allowed_tools: Sequence[str] | None = None) -> AgentResult:
        session = LilbotSession(user_query=request)
        answer = self.controller.run(session, allowed_tools=allowed_tools)
        return AgentResult(answer=answer, session=session)
