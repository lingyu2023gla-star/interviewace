"""Evidence-based advice prompt tests."""

from __future__ import annotations

from prompts.evidence_based_advice import build_evidence_based_advice_prompt


def test_build_prompt_contains_goal_job_and_evidence() -> None:
    prompt = build_evidence_based_advice_prompt(
        user_goal="准备 Agent/RAG 应用工程师面试",
        job_direction="大模型应用工程师",
        evidence_context="[E1]\n证据内容：Agent 架构复盘",
    )

    assert "准备 Agent/RAG 应用工程师面试" in prompt
    assert "大模型应用工程师" in prompt
    assert "[E1]" in prompt
    assert "历史证据" in prompt


def test_build_prompt_contains_citation_rules() -> None:
    prompt = build_evidence_based_advice_prompt(
        user_goal="准备面试",
        evidence_context="[E1]\n证据内容",
    )

    assert "只能基于【历史证据】" in prompt
    assert "必须引用证据编号" in prompt
    assert "历史证据不足" in prompt
    assert "不能编造" in prompt
    assert "不能把建议写成候选人已经做到" in prompt


def test_build_prompt_contains_output_sections() -> None:
    prompt = build_evidence_based_advice_prompt(
        user_goal="准备面试",
        evidence_context="[E1]\n证据内容",
    )

    assert "# 1. 基于历史证据的判断" in prompt
    assert "# 2. 下一次面试具体建议" in prompt
    assert "# 3. 证据不足但建议主动展示的能力" in prompt
    assert "# 4. 禁止过度包装提醒" in prompt


def test_build_prompt_respects_max_suggestions() -> None:
    prompt = build_evidence_based_advice_prompt(
        user_goal="准备面试",
        evidence_context="[E1]\n证据内容",
        max_suggestions=3,
    )

    assert "最多输出 3 条" in prompt


def test_build_prompt_handles_empty_evidence_context() -> None:
    prompt = build_evidence_based_advice_prompt(
        user_goal="准备面试",
        evidence_context="无可用历史证据。",
    )

    assert "当前没有历史证据可引用" in prompt
    assert "不要生成具体历史表现判断" in prompt
