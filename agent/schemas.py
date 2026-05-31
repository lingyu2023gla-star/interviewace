from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Intent(Enum):
    ANALYZE_INTERVIEW = "analyze_interview"
    REVIEW_HISTORY = "review_history"
    PRACTICE_QUESTIONS = "practice_questions"
    PLAN_PREPARATION = "plan_preparation"
    CHECK_GROWTH = "check_growth"


@dataclass
class ToolResult:
    success: bool
    data: dict | list | str | None
    error: str | None = None

    def unwrap(self) -> Any:
        """成功时返回 data，失败时抛出 RuntimeError。"""
        if not self.success:
            raise RuntimeError(self.error or "ToolResult failed")
        return self.data


@dataclass
class AgentContext:
    intent: Intent
    user_input: dict
    job_direction: str = ""
    tool_results: dict[str, ToolResult] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)
    current_step: int = 0
    errors: list[str] = field(default_factory=list)

    def get(self, path: str) -> Any:
        """
        按点分路径从 context 取值。
        支持：
          user_input.text
          tool_results.parse_interview.data.turns
        """
        parts = path.split(".")
        obj: Any = self
        for part in parts:
            if isinstance(obj, dict):
                obj = obj[part]
            else:
                obj = getattr(obj, part)
        return obj
