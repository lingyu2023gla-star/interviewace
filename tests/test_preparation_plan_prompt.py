"""Preparation plan prompt builder tests."""

from __future__ import annotations

import pytest

from prompts.preparation_plan import build_preparation_plan_prompt


def test_build_prompt_contains_core_inputs() -> None:
    prompt = build_preparation_plan_prompt(
        user_goal="准备 Agent/RAG 应用工程师面试",
        job_direction="大模型应用工程师",
        evidence_context="[E1]\n证据内容：候选人讲到了 Orchestrator。",
        plan_days=7,
        daily_minutes=60,
        max_tasks_per_day=3,
    )

    assert "准备 Agent/RAG 应用工程师面试" in prompt
    assert "大模型应用工程师" in prompt
    assert "7 天" in prompt
    assert "60 分钟" in prompt
    assert "每日最多任务数" in prompt
    assert "[E1]" in prompt
    assert "Orchestrator" in prompt


def test_build_prompt_contains_evidence_rules() -> None:
    prompt = build_preparation_plan_prompt(
        user_goal="准备面试",
        evidence_context="[E1]\n证据内容",
    )

    assert "只能基于【历史证据】" in prompt
    assert "必须引用证据编号" in prompt
    assert "历史证据不足" in prompt
    assert "不能编造" in prompt
    assert "不能把建议写成候选人已经做到" in prompt


def test_build_prompt_contains_output_sections() -> None:
    prompt = build_preparation_plan_prompt(
        user_goal="准备面试",
        evidence_context="[E1]\n证据内容",
        plan_days=7,
    )

    assert "# 1. 准备重点判断" in prompt
    assert "# 2. 7 天准备计划" in prompt
    assert "# 3. 重点问题回答模板" in prompt
    assert "# 4. 需要主动展示但历史证据不足的能力" in prompt
    assert "# 5. 过度包装风险提醒" in prompt


def test_build_prompt_respects_plan_params() -> None:
    prompt = build_preparation_plan_prompt(
        user_goal="准备面试",
        evidence_context="[E1]\n证据内容",
        plan_days=3,
        daily_minutes=30,
        max_tasks_per_day=2,
    )

    assert "3 天准备计划" in prompt
    assert "30 分钟" in prompt
    assert "每天任务数不能超过 2" in prompt


def test_build_prompt_empty_evidence_context() -> None:
    prompt = build_preparation_plan_prompt(
        user_goal="准备面试",
        evidence_context="",
    )

    assert "无可用历史证据" in prompt
    assert "不要生成任何关于候选人历史表现的判断" in prompt
    assert "不要引用不存在的 [E1]" in prompt
    assert "当前没有历史证据可引用" in prompt


def test_build_prompt_invalid_user_goal() -> None:
    with pytest.raises(ValueError):
        build_preparation_plan_prompt(user_goal="", evidence_context="[E1]")


def test_build_prompt_invalid_plan_days() -> None:
    with pytest.raises(ValueError):
        build_preparation_plan_prompt(user_goal="准备面试", evidence_context="[E1]", plan_days=0)


def test_build_prompt_invalid_daily_minutes() -> None:
    with pytest.raises(ValueError):
        build_preparation_plan_prompt(user_goal="准备面试", evidence_context="[E1]", daily_minutes=0)


def test_build_prompt_invalid_max_tasks_per_day() -> None:
    with pytest.raises(ValueError):
        build_preparation_plan_prompt(user_goal="准备面试", evidence_context="[E1]", max_tasks_per_day=0)
