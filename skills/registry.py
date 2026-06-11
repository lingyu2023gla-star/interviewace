"""Registry for InterviewAce skill implementations."""

from __future__ import annotations

from skills.base import BaseSkill
from skills.schemas import SkillSpec


class SkillRegistryError(Exception):
    """Base error for skill registry operations."""


class SkillAlreadyRegisteredError(SkillRegistryError):
    """Raised when registering a duplicate skill name."""


class SkillNotFoundError(SkillRegistryError):
    """Raised when a requested skill is not registered."""


class SkillRegistry:
    """In-memory registry for skill implementations."""

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """Register a skill by its spec name."""
        if not isinstance(skill, BaseSkill):
            raise TypeError("skill must be an instance of BaseSkill")

        name = skill.spec.name
        if not name or not name.strip():
            raise ValueError("skill.spec.name must be non-empty")
        if name in self._skills:
            raise SkillAlreadyRegisteredError(f"Skill already registered: {name}")
        self._skills[name] = skill

    def get(self, name: str) -> BaseSkill:
        """Return a registered skill by name."""
        if name in self._skills:
            return self._skills[name]
        raise SkillNotFoundError(f"Skill not found: {name}")

    def has(self, name: str) -> bool:
        """Return whether a skill name is registered."""
        return name in self._skills

    def list_specs(self) -> list[SkillSpec]:
        """Return registered skill specs sorted by name."""
        return [self._skills[name].spec for name in self.list_names()]

    def list_names(self) -> list[str]:
        """Return registered skill names sorted lexicographically."""
        return sorted(self._skills)


def create_default_registry() -> SkillRegistry:
    """Create an empty default registry for future business skills."""
    return SkillRegistry()
