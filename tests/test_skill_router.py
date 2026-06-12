"""Rule-based skill router tests."""

from __future__ import annotations

from skills import (
    BaseSkill,
    RuleBasedSkillRouter,
    SkillRegistry,
    SkillRequest,
    SkillResult,
    SkillRouteRequest,
    SkillSpec,
    create_default_skill_registry,
)


class ExplodingSkill(BaseSkill):
    """Skill that would fail if the router executed it."""

    @property
    def spec(self) -> SkillSpec:
        return SkillSpec(
            name="explode",
            description="Exploding skill for routing tests.",
            input_schema={},
            output_schema={},
            supported_retriever_types=("keyword",),
            tags=("project",),
        )

    def run(self, request: SkillRequest) -> SkillResult:
        raise AssertionError("router must not execute skill.run")


def _router() -> RuleBasedSkillRouter:
    return RuleBasedSkillRouter(create_default_skill_registry())


def test_explicit_skill_name_existing_takes_priority() -> None:
    result = _router().route(
        SkillRouteRequest(
            text="我要做项目讲解",
            explicit_skill_name="interview_preparation",
        )
    )

    assert result.selected_skill_name == "interview_preparation"
    assert result.confidence == 1.0
    assert "Explicit" in result.reason


def test_explicit_skill_name_missing_returns_none() -> None:
    result = _router().route(SkillRouteRequest(text="我要准备面试", explicit_skill_name="unknown"))

    assert result.selected_skill_name is None
    assert result.confidence == 0.0
    assert "not registered" in result.reason


def test_route_interview_preparation_by_chinese_keyword() -> None:
    result = _router().route(SkillRouteRequest(text="帮我做一份面试准备"))

    assert result.selected_skill_name == "interview_preparation"
    assert 0.0 < result.confidence <= 1.0


def test_route_interview_preparation_by_plan_keyword() -> None:
    result = _router().route(SkillRouteRequest(text="生成下一阶段准备计划"))

    assert result.selected_skill_name == "interview_preparation"


def test_route_project_pitch_by_chinese_keyword() -> None:
    result = _router().route(SkillRouteRequest(text="帮我整理 InterviewAce 项目讲解"))

    assert result.selected_skill_name == "project_pitch"


def test_route_project_pitch_by_intro_keyword() -> None:
    result = _router().route(SkillRouteRequest(text="准备项目介绍话术"))

    assert result.selected_skill_name == "project_pitch"


def test_route_project_pitch_by_english_keyword() -> None:
    result = _router().route(SkillRouteRequest(text="generate a project pitch for my interview"))

    assert result.selected_skill_name == "project_pitch"


def test_route_no_match_returns_none() -> None:
    result = _router().route(SkillRouteRequest(text="今天午饭吃什么"))

    assert result.selected_skill_name is None
    assert result.confidence == 0.0


def test_route_does_not_execute_skill_run() -> None:
    registry = SkillRegistry()
    registry.register(ExplodingSkill())
    router = RuleBasedSkillRouter(registry)

    result = router.route(SkillRouteRequest(text="project"))

    assert result.selected_skill_name == "explode"


def test_route_candidates_include_candidate_info() -> None:
    result = _router().route(SkillRouteRequest(text="项目介绍"))

    assert result.candidates
    assert {"skill_name", "score", "matches"}.issubset(result.candidates[0])


def test_route_confidence_is_between_zero_and_one() -> None:
    result = _router().route(SkillRouteRequest(text="project pitch 项目讲解 project_pitch"))

    assert 0.0 <= result.confidence <= 1.0


def test_route_empty_registry_does_not_crash() -> None:
    result = RuleBasedSkillRouter(SkillRegistry()).route(SkillRouteRequest(text="面试准备"))

    assert result.selected_skill_name is None
    assert result.candidates == []
