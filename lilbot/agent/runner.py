from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from lilbot.agent.context import AgentContext
from lilbot.agent.planner import Planner
from lilbot.llm.provider import LLMProvider
from lilbot.llm.prompt_builder import build_prompt
from lilbot.tools.registry import ToolRegistry


@dataclass
class AgentResult:
    final: str
    steps: int


class AgentRunner:
    def __init__(
        self,
        llm: LLMProvider,
        tools: ToolRegistry,
        planner: Optional[Planner] = None,
        context: Optional[AgentContext] = None,
        confirm: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.planner = planner or Planner()
        self.context = context or AgentContext()
        self.confirm = confirm

    def run(self, user_request: str) -> AgentResult:
        self.context.memory.add(f"User: {user_request}")

        for step in range(1, self.planner.max_steps + 1):
            prompt = build_prompt(
                user_request=user_request,
                memory=self.context.memory.render(),
                tools=self.tools.list_specs(),
                scratchpad=self.context.render_scratchpad(),
            )
            response = self.llm.generate(prompt)
            decision, payload = self._parse_response(response)

            if decision == "FINAL":
                self.context.memory.add(f"Agent: {payload}")
                return AgentResult(final=payload, steps=step)

            if decision == "TOOL":
                tool_name, tool_input = payload
                result = self.tools.execute(
                    tool_name,
                    tool_input,
                    confirm=self._confirm_tool,
                )
                self.context.add_observation(f"Tool {tool_name} result: {result}")
                continue

            self.context.add_observation("Unrecognized model output; stopping.")
            return AgentResult(final="Unable to complete task.", steps=step)

        return AgentResult(final="Max steps reached without completion.", steps=self.planner.max_steps)

    def _confirm_tool(self, tool) -> bool:
        if not self.confirm:
            return True
        return self.confirm(tool.name)

    def _parse_response(self, response: str) -> Tuple[str, Any]:
        lines = [line.strip() for line in response.splitlines() if line.strip()]
        if not lines:
            return "UNKNOWN", None

        if lines[0].startswith("FINAL:"):
            return "FINAL", lines[0].replace("FINAL:", "").strip()

        if lines[0].startswith("TOOL:"):
            tool_name = lines[0].replace("TOOL:", "").strip()
            tool_input = {}
            for line in lines[1:]:
                if line.startswith("INPUT:"):
                    raw = line.replace("INPUT:", "").strip()
                    try:
                        tool_input = json.loads(raw)
                    except json.JSONDecodeError:
                        tool_input = {"raw": raw}
                    break
            return "TOOL", (tool_name, tool_input)

        return "UNKNOWN", None
