"""
tests/test_orchestrator.py — agent 层纯逻辑单元测试
"""

from __future__ import annotations

import time

import pytest
from unittest.mock import patch

from agent.orchestrator import InterviewOrchestrator
from agent.schemas import AgentContext, Intent, ToolResult
from agent.tools import (
    tool_analyze_topics,
    tool_group_topics,
    tool_parse_interview,
)


def _sample_text() -> str:
    return """AI应用开发面试
说话人2 00:00
请介绍一个你做过的 Agent 项目。

说话人1 00:12
我负责设计一个面向企业知识库的 Agent 系统，主要完成需求拆解、工具调用编排和效果评估，并通过日志分析持续优化回答质量。
"""


# ── 1. agent/schemas.py ─────────────────────────────────────────────────────

def test_tool_result_unwrap_success() -> None:
    result = ToolResult(success=True, data={"ok": 1})
    assert result.unwrap() == {"ok": 1}


def test_tool_result_unwrap_failure() -> None:
    result = ToolResult(success=False, data=None, error="boom")
    with pytest.raises(RuntimeError, match="boom"):
        result.unwrap()


def test_agent_context_get_user_input() -> None:
    ctx = AgentContext(
        intent=Intent.ANALYZE_INTERVIEW,
        user_input={"text": "hello"},
    )
    assert ctx.get("user_input.text") == "hello"


def test_agent_context_get_nested() -> None:
    ctx = AgentContext(
        intent=Intent.ANALYZE_INTERVIEW,
        user_input={},
        tool_results={
            "parse_interview": ToolResult(
                success=True,
                data={"turns": [{"speaker": "candidate"}]},
            )
        },
    )
    assert ctx.get("tool_results.parse_interview.data.turns") == [{"speaker": "candidate"}]


# ── 2. agent/tools.py — tool_parse_interview ────────────────────────────────

def test_tool_parse_interview_success() -> None:
    result = tool_parse_interview(_sample_text())

    assert result.success is True
    assert result.data["title"] == "AI应用开发面试"
    assert len(result.data["turns"]) == 2
    assert len(result.data["pairs"]) == 1
    assert result.data["pairs"][0]["index"] == 1
    assert "Agent 项目" in result.data["pairs"][0]["question"]


def test_tool_parse_interview_empty_text() -> None:
    result = tool_parse_interview("")

    assert result.success is False or result.data.get("pairs") == []


# ── 3. agent/tools.py — tool_group_topics ───────────────────────────────────

def test_tool_group_topics_success() -> None:
    pairs = [{"index": 1, "question": "Q1", "answer": "A1"}]
    groups = [{"topic": "项目经验", "turns": [1]}]

    with patch("agent.tools.group_turns", return_value=groups):
        result = tool_group_topics(pairs)

    assert result.success is True
    assert result.data["groups"] == groups


def test_tool_group_topics_fallback() -> None:
    pairs = [{"index": 1, "question": "Q1", "answer": "A1"}]

    with patch("agent.tools.group_turns", side_effect=RuntimeError("group failed")):
        result = tool_group_topics(pairs)

    assert result.success is False
    assert "group failed" in result.error


# ── 4. agent/tools.py — tool_analyze_topics ─────────────────────────────────

def test_tool_analyze_topics_success() -> None:
    groups = [
        {"topic": "项目经验", "turns": [1]},
        {"topic": "技术深度", "turns": [2]},
        {"topic": "协作沟通", "turns": [3]},
    ]
    pairs = [
        {"index": 1, "question": "Q1", "answer": "A1"},
        {"index": 2, "question": "Q2", "answer": "A2"},
        {"index": 3, "question": "Q3", "answer": "A3"},
    ]

    def fake_analyze_turn(question: str, answer: str, job_direction: str) -> dict:
        if question == "[1] Q1":
            time.sleep(0.03)
        return {
            "star_completeness": {
                "situation": f"固定反馈-{question}",
                "task": "",
                "action": "",
                "result": "",
            },
            "accuracy": f"准确性-{question}",
            "logic": f"逻辑-{question}",
            "grade": "良好",
            "reference_answer": f"参考-{question}",
            "improvements": [
                {"problem": f"问题-{question}", "suggestion": "改进", "practice": "练习"}
            ],
        }

    with patch("agent.tools.analyze_turn", side_effect=fake_analyze_turn):
        result = tool_analyze_topics(groups, pairs, "AI应用开发")

    assert result.success is True
    feedbacks = result.data["feedbacks"]
    assert len(feedbacks) == 3
    assert [item["index"] for item in feedbacks] == [1, 2, 3]
    assert feedbacks[0]["index"] == 1
    assert feedbacks[0]["topic"] == "项目经验"
    assert feedbacks[0]["question"] == "[1] Q1"
    assert feedbacks[0]["answer"] == "[1] A1"
    assert "固定反馈-[1] Q1" in feedbacks[0]["feedback"]
    assert feedbacks[0]["feedback_dict"]["grade"] == "良好"
    assert feedbacks[1]["index"] == 2
    assert feedbacks[1]["topic"] == "技术深度"
    assert feedbacks[1]["question"] == "[2] Q2"
    assert feedbacks[1]["answer"] == "[2] A2"
    assert "固定反馈-[2] Q2" in feedbacks[1]["feedback"]
    assert feedbacks[1]["feedback_dict"]["grade"] == "良好"
    assert feedbacks[2]["index"] == 3
    assert feedbacks[2]["topic"] == "协作沟通"
    assert feedbacks[2]["question"] == "[3] Q3"
    assert feedbacks[2]["answer"] == "[3] A3"
    assert "固定反馈-[3] Q3" in feedbacks[2]["feedback"]
    assert feedbacks[2]["feedback_dict"]["grade"] == "良好"


def test_tool_analyze_topics_empty_groups() -> None:
    result = tool_analyze_topics([], [], "AI应用开发")

    assert result.success is True
    assert result.data["feedbacks"] == []


# ── 5. agent/orchestrator.py — run_analyze_interview ────────────────────────

def test_run_analyze_interview_parse_failure() -> None:
    orchestrator = InterviewOrchestrator()

    with patch(
        "agent.orchestrator.tool_parse_interview",
        return_value=ToolResult(success=False, data=None, error="parse failed"),
    ):
        result = orchestrator.run_analyze_interview("bad text", "AI应用开发")

    assert result.success is False
    assert "文件解析失败" in result.error


def test_run_analyze_interview_empty_pairs() -> None:
    orchestrator = InterviewOrchestrator()

    with patch(
        "agent.orchestrator.tool_parse_interview",
        return_value=ToolResult(success=True, data={"pairs": []}),
    ):
        result = orchestrator.run_analyze_interview("text", "AI应用开发")

    assert result.success is False
    assert "有效问答" in result.error


def test_run_analyze_interview_group_fallback() -> None:
    orchestrator = InterviewOrchestrator()
    pairs = [{"index": 1, "question": "Q1", "answer": "A1"}]
    feedbacks = [{"index": 1, "topic": "第1轮", "question": "[1] Q1", "answer": "[1] A1", "feedback": "反馈"}]

    with (
        patch("agent.orchestrator.tool_parse_interview", return_value=ToolResult(success=True, data={"pairs": pairs})),
        patch("agent.orchestrator.tool_group_topics", return_value=ToolResult(success=False, data=None, error="group failed")),
        patch("agent.orchestrator.tool_analyze_topics", return_value=ToolResult(success=True, data={"feedbacks": feedbacks})) as mock_analyze,
        patch("agent.orchestrator.tool_generate_summary", return_value=ToolResult(success=True, data={"summary": "总结"})),
        patch("agent.orchestrator.tool_score_performance", return_value=ToolResult(success=True, data={"scores": None})),
        patch("agent.orchestrator.tool_save_results", return_value=ToolResult(success=True, data={"session_id": 1, "questions_saved": 0})),
    ):
        result = orchestrator.run_analyze_interview("text", "AI应用开发")

    assert result.success is True
    mock_analyze.assert_called_once()
    groups_arg = mock_analyze.call_args.args[0]
    assert groups_arg == [{"topic": "第1轮", "turns": [1]}]


def test_run_analyze_interview_success() -> None:
    orchestrator = InterviewOrchestrator()
    pairs = [{"index": 1, "question": "Q1", "answer": "A1"}]
    groups = [{"topic": "项目经验", "turns": [1]}]
    feedbacks = [{"index": 1, "topic": "项目经验", "question": "[1] Q1", "answer": "[1] A1", "feedback": "反馈"}]
    scores = {"logical_clarity": {"score": 8, "reason": "清晰"}}

    def fake_save_results(*args, **kwargs):
        kwargs["session_id_holder"].append(42)
        return ToolResult(success=True, data={"session_id": 42, "questions_saved": 1})

    with (
        patch("agent.orchestrator.tool_parse_interview", return_value=ToolResult(success=True, data={"pairs": pairs})),
        patch("agent.orchestrator.tool_group_topics", return_value=ToolResult(success=True, data={"groups": groups})),
        patch("agent.orchestrator.tool_analyze_topics", return_value=ToolResult(success=True, data={"feedbacks": feedbacks})),
        patch("agent.orchestrator.tool_generate_summary", return_value=ToolResult(success=True, data={"summary": "总结"})),
        patch("agent.orchestrator.tool_score_performance", return_value=ToolResult(success=True, data={"scores": scores})),
        patch("agent.orchestrator.tool_save_results", side_effect=fake_save_results),
    ):
        result = orchestrator.run_analyze_interview("text", "AI应用开发", title="测试面试")

    assert result.success is True
    assert result.data["session_id"] == 42
    assert result.data["feedbacks"] == feedbacks
    assert result.data["summary"] == "总结"
    assert result.data["scores"] == scores
    assert result.data["questions_saved"] == 1
    assert result.data["title"] == "测试面试"
    assert result.data["groups_count"] == 1
