"""Rule-based routing for selecting InterviewAce skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skills.registry import SkillRegistry


@dataclass(frozen=True)
class SkillRouteRequest:
    """Input for selecting a skill from user intent."""

    text: str
    explicit_skill_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate route request shape."""
        if not isinstance(self.text, str):
            raise ValueError("text must be a string")
        if self.explicit_skill_name is not None and not isinstance(self.explicit_skill_name, str):
            raise ValueError("explicit_skill_name must be a string or None")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dict")


@dataclass(frozen=True)
class SkillRouteResult:
    """Result of rule-based skill routing."""

    selected_skill_name: str | None
    confidence: float
    reason: str
    candidates: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Clamp confidence into a stable range."""
        confidence = max(0.0, min(1.0, float(self.confidence)))
        object.__setattr__(self, "confidence", confidence)


_SKILL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "interview_preparation": (
        "prepare",
        "preparation",
        "interview plan",
        "面试准备",
        "准备计划",
        "复习计划",
    ),
    "project_pitch": (
        "project pitch",
        "project intro",
        "项目讲解",
        "项目介绍",
        "项目话术",
        "讲项目",
    ),
}


def _normalize_text(text: str) -> str:
    """Normalize text for simple rule matching."""
    return " ".join(text.lower().split())


def _clamp_score(score: float) -> float:
    """Clamp a route score to the confidence range."""
    return max(0.0, min(1.0, score))


class RuleBasedSkillRouter:
    """Select a skill by explicit name or lightweight keyword matching."""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def route(self, request: SkillRouteRequest) -> SkillRouteResult:
        """Route user intent to a registered skill without executing it."""
        explicit_name = (request.explicit_skill_name or "").strip()
        if explicit_name:
            if self.registry.has(explicit_name):
                return SkillRouteResult(
                    selected_skill_name=explicit_name,
                    confidence=1.0,
                    reason=f"Explicit skill_name matched: {explicit_name}",
                    candidates=[
                        {
                            "skill_name": explicit_name,
                            "score": 1.0,
                            "matches": ["explicit_skill_name"],
                        }
                    ],
                )
            return SkillRouteResult(
                selected_skill_name=None,
                confidence=0.0,
                reason=f"Explicit skill_name is not registered: {explicit_name}",
                candidates=[],
            )

        normalized_text = _normalize_text(request.text)
        candidates = []
        for spec in self.registry.list_specs():
            score = 0.0
            matches: list[str] = []

            normalized_name = _normalize_text(spec.name)
            if normalized_name and normalized_name in normalized_text:
                score += 0.8
                matches.append("skill_name")

            for tag in spec.tags:
                normalized_tag = _normalize_text(str(tag))
                if normalized_tag and normalized_tag in normalized_text:
                    score += 0.5
                    matches.append(f"tag:{tag}")

            for keyword in _SKILL_KEYWORDS.get(spec.name, ()):
                normalized_keyword = _normalize_text(keyword)
                if normalized_keyword and normalized_keyword in normalized_text:
                    score += 0.6
                    matches.append(f"keyword:{keyword}")

            description = _normalize_text(spec.description)
            for token in normalized_text.split():
                if len(token) >= 4 and token in description:
                    score += 0.3
                    matches.append("description")
                    break

            candidates.append(
                {
                    "skill_name": spec.name,
                    "score": _clamp_score(score),
                    "matches": matches,
                }
            )

        candidates.sort(key=lambda item: (-item["score"], item["skill_name"]))
        if not candidates or candidates[0]["score"] <= 0:
            return SkillRouteResult(
                selected_skill_name=None,
                confidence=0.0,
                reason="No registered skill matched the request text.",
                candidates=candidates,
            )

        selected = candidates[0]
        return SkillRouteResult(
            selected_skill_name=selected["skill_name"],
            confidence=selected["score"],
            reason=f"Matched by rule-based signals: {', '.join(selected['matches'])}",
            candidates=candidates,
        )
