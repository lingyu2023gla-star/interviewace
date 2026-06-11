"""Evidence reference validator tests."""

from __future__ import annotations

from preparation.evidence_validator import (
    extract_evidence_refs_from_text,
    extract_valid_evidence_ids,
    normalize_evidence_ref,
    validate_evidence_refs,
    validate_structured_plan_evidence_refs,
)
from preparation.structured_schemas import StructuredPreparationPlan


def _valid_plan_data(evidence_refs=None) -> dict:
    refs = ["E1"] if evidence_refs is None else evidence_refs
    return {
        "summary": "基于历史证据准备 Agent 架构。",
        "evidence_based_judgments": [
            {
                "type": "strength",
                "content": "候选人讲到了 Orchestrator 和 ToolResult。",
                "evidence_refs": refs,
            }
        ],
        "daily_plan": [
            {
                "day": 1,
                "goal": "整理 Agent 架构回答",
                "tasks": [
                    {
                        "task": "准备回答模板",
                        "estimated_minutes": 30,
                        "output": "模板",
                        "evidence_refs": [],
                    }
                ],
            }
        ],
        "question_templates": [
            {
                "question": "请介绍 Agent 架构",
                "answer_goal": "讲清编排和工具调用",
                "answer_structure": ["结论", "原因", "证据"],
                "sample_answer": "我会结合项目说明。",
                "evidence_refs": [],
            }
        ],
        "abilities_to_show": [
            {
                "ability": "RAG",
                "why_needed": "目标岗位需要",
                "current_evidence_status": "历史证据不足",
                "how_to_show_next_time": "主动说明边界",
            }
        ],
        "risk_warnings": [
            {
                "risk": "不要过度包装 RAG",
                "reason": "历史证据不足",
                "evidence_refs": [],
            }
        ],
        "metadata": {},
    }


def _issue_codes(result) -> set[str]:
    return {issue.code for issue in result.issues}


def test_extract_valid_evidence_ids() -> None:
    context = "[E1]\n证据内容\n\n[E2]\n证据内容\n\n普通文本 [E2]"

    assert extract_valid_evidence_ids(context) == {"E1", "E2"}


def test_extract_valid_evidence_ids_empty_context() -> None:
    assert extract_valid_evidence_ids("") == set()
    assert extract_valid_evidence_ids(None) == set()


def test_extract_evidence_refs_from_text_bracket_ref() -> None:
    assert extract_evidence_refs_from_text("依据 [E1] 判断") == {"E1"}


def test_extract_evidence_refs_from_text_multiple_refs() -> None:
    text = "依据 [E1] 和 E2 判断，但 userE3@example.com 不应被当作引用。"

    assert extract_evidence_refs_from_text(text) == {"E1", "E2"}


def test_normalize_evidence_ref() -> None:
    assert normalize_evidence_ref("[e1]") == "E1"
    assert normalize_evidence_ref(" e2 ") == "E2"


def test_validate_evidence_refs_unknown_ref() -> None:
    issues = validate_evidence_refs({"E1", "E9"}, {"E1", "E2"}, "field")

    assert len(issues) == 1
    assert issues[0].code == "unknown_evidence_ref"
    assert issues[0].evidence_ref == "E9"


def test_validate_evidence_refs_all_valid() -> None:
    assert validate_evidence_refs({"E1"}, {"E1", "E2"}) == []


def test_validate_structured_plan_evidence_refs_valid_dict() -> None:
    result = validate_structured_plan_evidence_refs(_valid_plan_data(), "[E1]\n证据")

    assert result.is_valid is True
    assert result.valid_evidence_ids == {"E1"}
    assert result.used_evidence_refs == {"E1"}


def test_validate_structured_plan_evidence_refs_unknown_ref() -> None:
    data = _valid_plan_data(evidence_refs=["E9"])

    result = validate_structured_plan_evidence_refs(data, "[E1]\n证据")

    assert result.is_valid is False
    assert "unknown_evidence_ref" in _issue_codes(result)


def test_validate_structured_plan_evidence_refs_missing_required_ref() -> None:
    data = _valid_plan_data(evidence_refs=[])

    result = validate_structured_plan_evidence_refs(data, "[E1]\n证据")

    assert result.is_valid is False
    assert "missing_required_evidence_ref" in _issue_codes(result)


def test_validate_structured_plan_empty_context_with_concrete_judgment() -> None:
    result = validate_structured_plan_evidence_refs(_valid_plan_data(evidence_refs=[]), "")

    assert result.is_valid is False
    assert "empty_evidence_context_with_judgment" in _issue_codes(result)


def test_validate_structured_plan_suggestion_fields_without_refs_do_not_fail() -> None:
    data = _valid_plan_data(evidence_refs=["E1"])
    data["daily_plan"][0]["tasks"][0]["evidence_refs"] = []
    data["question_templates"][0]["evidence_refs"] = []

    result = validate_structured_plan_evidence_refs(data, "[E1]\n证据")

    assert result.is_valid is True


def test_validate_structured_plan_suggestion_unknown_ref_fails() -> None:
    data = _valid_plan_data(evidence_refs=["E1"])
    data["daily_plan"][0]["tasks"][0]["evidence_refs"] = ["E9"]

    result = validate_structured_plan_evidence_refs(data, "[E1]\n证据")

    assert result.is_valid is False
    assert "unknown_evidence_ref" in _issue_codes(result)


def test_validate_structured_plan_accepts_pydantic_model() -> None:
    plan = StructuredPreparationPlan(**_valid_plan_data())

    result = validate_structured_plan_evidence_refs(plan, "[E1]\n证据")

    assert result.is_valid is True


def test_validate_structured_plan_without_judgments_does_not_crash() -> None:
    data = _valid_plan_data()
    data["evidence_based_judgments"] = []

    result = validate_structured_plan_evidence_refs(data, "")

    assert result.is_valid is True


def test_validate_structured_plan_empty_input_does_not_crash() -> None:
    result = validate_structured_plan_evidence_refs({}, "")

    assert result.is_valid is True
