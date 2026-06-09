"""Prompt builder tests."""

from __future__ import annotations

import pytest

from core import analyzer
from prompts.dimensions import DiagnosisDimension
from prompts.interview_analysis import build_full_context_analysis_prompt


def test_default_full_context_prompt_renders() -> None:
    prompt = build_full_context_analysis_prompt(
        full_text="面试官：请介绍 Agent 项目",
        job_direction="大模型应用工程师",
    )

    assert "大模型应用工程师" in prompt
    assert "面试官：请介绍 Agent 项目" in prompt
    assert "Prompt 工程能力" in prompt
    assert "Agent 架构能力" in prompt


def test_custom_dimensions_override_defaults() -> None:
    prompt = build_full_context_analysis_prompt(
        full_text="完整文本",
        job_direction="AI 工程师",
        dimensions=[
            DiagnosisDimension(
                key="custom_dimension",
                name="自定义能力",
                focus="只检查这个自定义维度。",
            )
        ],
    )

    assert "自定义能力" in prompt
    assert "Prompt 工程能力" not in prompt


def test_empty_dimensions_raise_value_error() -> None:
    with pytest.raises(ValueError, match="能力诊断维度不能为空"):
        build_full_context_analysis_prompt(
            full_text="完整文本",
            job_direction="AI 工程师",
            dimensions=[],
        )


def test_invalid_dimension_profile_raise_value_error() -> None:
    with pytest.raises(ValueError, match="可用 profile"):
        build_full_context_analysis_prompt(
            full_text="完整文本",
            job_direction="AI 工程师",
            dimension_profile="unknown",
        )


def test_max_suggestions_renders() -> None:
    prompt = build_full_context_analysis_prompt(
        full_text="完整文本",
        job_direction="AI 工程师",
        max_suggestions=3,
    )

    assert "只列出最值得改的 3 个问题" in prompt


def test_analyze_full_interview_calls_prompt_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_messages: list[dict] = []

    class FakeMessage:
        content = "完整复盘报告"

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, *, model: str, messages: list[dict], timeout: int) -> FakeResponse:
            captured_messages.extend(messages)
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    def fake_builder(full_text: str, job_direction: str = "") -> str:
        assert full_text == "完整面试文本"
        assert job_direction == "AI应用开发"
        return "BUILDER_PROMPT"

    monkeypatch.setattr(analyzer, "build_full_context_analysis_prompt", fake_builder)
    monkeypatch.setattr(analyzer, "_get_client", lambda: FakeClient())

    result = analyzer.analyze_full_interview("完整面试文本", "AI应用开发")

    assert result == "完整复盘报告"
    assert captured_messages == [{"role": "user", "content": "BUILDER_PROMPT"}]
