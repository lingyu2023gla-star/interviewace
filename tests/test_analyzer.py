"""
tests/test_analyzer.py — core/analyzer.py pure logic tests
"""

from __future__ import annotations

from unittest.mock import patch

from core.analyzer import (
    _strip_markdown_fence,
    _validate_groups,
    _validate_scores,
    analyze_turn,
    extract_mock_rating,
    extract_questions,
)


# ── 1. Markdown fence stripping ───────────────────────────────────────────────

def test_strip_json_fence() -> None:
    assert _strip_markdown_fence("```json\n{}\n```") == "{}"


def test_strip_plain_fence() -> None:
    assert _strip_markdown_fence("```\nhello\n```") == "hello"


def test_no_fence() -> None:
    assert _strip_markdown_fence("hello") == "hello"


def test_strip_with_whitespace() -> None:
    assert _strip_markdown_fence("  ```json\n{}\n```  ") == "{}"


# ── 2. Group JSON validation ─────────────────────────────────────────────────

def test_valid_groups() -> None:
    data = [
        {"topic": "自我介绍", "turns": [1]},
        {"topic": "技术深度", "turns": [2, 3]},
    ]
    assert _validate_groups(data) is True


def test_invalid_not_list() -> None:
    assert _validate_groups({"topic": "自我介绍", "turns": [1]}) is False


def test_invalid_missing_topic() -> None:
    assert _validate_groups([{"turns": [1]}]) is False


def test_invalid_turns_not_list() -> None:
    assert _validate_groups([{"topic": "自我介绍", "turns": "1"}]) is False


def test_invalid_turns_not_int() -> None:
    assert _validate_groups([{"topic": "自我介绍", "turns": [1, "2"]}]) is False


# ── 3. Score JSON validation ─────────────────────────────────────────────────

def _valid_scores() -> dict:
    return {
        "star_completeness": {"score": 6, "reason": "STAR 基本完整"},
        "technical_depth": {"score": 7, "reason": "技术理解较深"},
        "logical_clarity": {"score": 5, "reason": "逻辑一般"},
        "proactiveness": {"score": 4, "reason": "主动性不足"},
        "result_orientation": {"score": 8, "reason": "结果量化清晰"},
    }


def test_valid_scores() -> None:
    assert _validate_scores(_valid_scores()) is True


def test_invalid_missing_key() -> None:
    data = _valid_scores()
    del data["technical_depth"]
    assert _validate_scores(data) is False


def test_invalid_score_out_of_range() -> None:
    data = _valid_scores()
    data["star_completeness"]["score"] = 11
    assert _validate_scores(data) is False


def test_invalid_score_not_int() -> None:
    data = _valid_scores()
    data["star_completeness"]["score"] = "6"
    assert _validate_scores(data) is False


def test_invalid_reason_not_str() -> None:
    data = _valid_scores()
    data["star_completeness"]["reason"] = 123
    assert _validate_scores(data) is False


# ── 4. Question extraction ───────────────────────────────────────────────────

def test_extract_with_reference_answer() -> None:
    feedback = {
        "reference_answer": "- Situation：说明背景\n- Task：明确目标",
        "grade": "良好",
    }
    result = extract_questions("系统设计", "请介绍一个项目。", feedback)

    assert result is not None
    assert result["topic"] == "系统设计"
    assert result["question"] == "请介绍一个项目。"
    assert result["reference_answer"] == "- Situation：说明背景\n- Task：明确目标"


def test_extract_no_reference_answer() -> None:
    result = extract_questions("系统设计", "请介绍一个项目。", {"grade": "一般"})

    assert result is not None
    assert result["reference_answer"] == ""


def test_extract_difficulty_hard() -> None:
    result = extract_questions("系统设计", "请介绍一个项目。", {"grade": "待改进"})

    assert result is not None
    assert result["difficulty"] == "hard"


def test_extract_difficulty_easy() -> None:
    result = extract_questions("系统设计", "请介绍一个项目。", {"grade": "优秀"})

    assert result is not None
    assert result["difficulty"] == "easy"


def test_extract_empty_topic_returns_none() -> None:
    assert extract_questions("", "请介绍一个项目。", {"grade": "优秀"}) is None


# ── 5. Mock interview rating extraction ─────────────────────────────────────

def test_extract_mock_rating_优秀() -> None:
    feedback = {"grade": "优秀"}
    assert extract_mock_rating(feedback) == "优秀"


def test_extract_mock_rating_待改进() -> None:
    feedback = {"grade": "待改进"}
    assert extract_mock_rating(feedback) == "待改进"


def test_extract_mock_rating_fallback() -> None:
    assert extract_mock_rating({}) == "一般"


def test_analyze_turn_fallback_structure() -> None:
    with patch("core.analyzer._get_client", side_effect=RuntimeError("boom")):
        result = analyze_turn("Q", "A", "AI应用开发")

    assert result["star_completeness"] == {
        "situation": "",
        "task": "",
        "action": "",
        "result": "",
    }
    assert result["accuracy"] == ""
    assert result["logic"] == ""
    assert result["grade"] == "一般"
    assert result["reference_answer"] == ""
    assert result["improvements"] == []
    assert result["_error"] == "分析失败，请重试"
