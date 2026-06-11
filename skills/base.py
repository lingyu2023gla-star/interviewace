"""Base abstraction for InterviewAce skills."""

from __future__ import annotations

from abc import ABC, abstractmethod

from skills.schemas import SkillRequest, SkillResult, SkillSpec


class BaseSkill(ABC):
    """Interface implemented by all InterviewAce skills."""

    @property
    @abstractmethod
    def spec(self) -> SkillSpec:
        """Return immutable skill metadata."""

    @abstractmethod
    def run(self, request: SkillRequest) -> SkillResult:
        """Execute the skill for one request."""

    @property
    def name(self) -> str:
        """Return the unique skill name."""
        return self.spec.name
