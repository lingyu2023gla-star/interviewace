"""
core/analyzer.py — 调用 DeepSeek API 完成面试复盘分析

使用 openai SDK，baseURL 指向 DeepSeek，API Key 从环境变量读取。
"""

from __future__ import annotations

import os
import json
import re

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from prompts.interview_analysis import (
    build_analysis_prompt,
    build_summary_prompt,
    build_grouping_prompt,
    build_scoring_prompt,
    build_mock_feedback_prompt,
    build_practice_plan_prompt,
    build_full_context_analysis_prompt,
)

load_dotenv()

_MODEL = "deepseek-chat"
_BASE_URL = "https://api.deepseek.com"
_API_TIMEOUT = 60  # 秒，单次 API 调用最长等待时间


def _get_client() -> OpenAI:
    """构造 OpenAI 兼容客户端，指向 DeepSeek。"""
    from httpx import Client as HttpxClient

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY 未设置")
    return OpenAI(
        api_key=api_key,
        base_url=_BASE_URL,
        http_client=HttpxClient(proxy=None),
    )


def _is_timeout(e: Exception) -> bool:
    """判断异常是否为超时。"""
    err = str(e).lower()
    return "timeout" in err or "timed out" in err


def _fallback_turn_analysis() -> dict:
    return {
        "star_completeness": {"situation": "", "task": "", "action": "", "result": ""},
        "accuracy": "",
        "logic": "",
        "grade": "一般",
        "reference_answer": "",
        "improvements": [],
        "_error": "分析失败，请重试",
    }


def _validate_turn_analysis(data: object) -> bool:
    """验证单轮分析 JSON 结构必须含核心字段。"""
    required_keys = {
        "star_completeness",
        "accuracy",
        "logic",
        "grade",
        "reference_answer",
        "improvements",
    }
    return isinstance(data, dict) and required_keys.issubset(data.keys())


def _fallback_mock_feedback() -> dict:
    return {
        "highlight": "",
        "problem": "",
        "suggestion": "",
        "grade": "一般",
        "_error": "反馈生成失败，请重试",
    }


def _validate_mock_feedback(data: object) -> bool:
    """验证模拟面试反馈 JSON 结构必须含核心字段。"""
    required_keys = {"highlight", "problem", "suggestion", "grade"}
    return isinstance(data, dict) and required_keys.issubset(data.keys())


def extract_questions(topic: str, question: str, feedback: dict) -> dict | None:
    """从单组分析反馈 dict 中提取题目信息，不调用 API。

    Args:
        topic: 话题名称。
        question: 合并后的面试问题文本。
        feedback: analyze_turn 返回的分析 dict。

    Returns:
        {"topic", "question", "reference_answer", "difficulty"}；
        topic 或 question 为空时返回 None。
    """
    if not topic or not question:
        return None

    reference_answer = feedback.get("reference_answer", "")
    grade = feedback.get("grade", "一般")
    difficulty_map = {"优秀": "easy", "良好": "easy", "一般": "medium", "待改进": "hard"}
    difficulty = difficulty_map.get(grade, "medium")

    return {
        "topic": topic,
        "question": question,
        "reference_answer": reference_answer,
        "difficulty": difficulty,
    }


def analyze_turn(question: str, answer: str, job_direction: str) -> dict:
    """对单个问答轮次调用 DeepSeek 完成面试复盘分析。

    Args:
        question: 面试官提出的问题。
        answer: 候选人的回答。
        job_direction: 应聘岗位方向，如「后端开发」。

    Returns:
        AI 生成的结构化分析 dict；调用失败时返回降级 dict。
    """
    prompt = build_analysis_prompt(question, answer, job_direction)
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=_API_TIMEOUT,
        )
        raw = response.choices[0].message.content or ""
        cleaned = _strip_markdown_fence(raw)
        data = json.loads(cleaned)
        if not _validate_turn_analysis(data):
            return _fallback_turn_analysis()
        return data
    except Exception:
        return _fallback_turn_analysis()


def analyze_full_interview(full_text: str, job_direction: str = "") -> str:
    """基于完整面试上下文调用 DeepSeek 生成全量复盘报告。

    Args:
        full_text: 已格式化的完整面试问答文本。
        job_direction: 应聘岗位方向。

    Returns:
        AI 生成的 Markdown 复盘报告；调用失败时返回友好错误提示。
    """
    prompt = build_full_context_analysis_prompt(full_text, job_direction)
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=_API_TIMEOUT,
        )
        return response.choices[0].message.content or ""
    except ValueError as e:
        return f"[配置错误] {e}"
    except OpenAIError as e:
        return f"[API 调用失败] {e}"
    except Exception as e:
        if _is_timeout(e):
            return "[API超时] DeepSeek 响应超时，请稍后重试"
        return f"[未知错误] {e}"


def analyze_mock_answer(question: str, answer: str, job_direction: str) -> dict:
    """对模拟面试单轮回答生成简短反馈。

    Returns:
        反馈 dict；失败时返回降级 dict。
    """
    prompt = build_mock_feedback_prompt(question, answer, job_direction)
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=_API_TIMEOUT,
        )
        raw = response.choices[0].message.content or ""
        cleaned = _strip_markdown_fence(raw)
        data = json.loads(cleaned)
        if not _validate_mock_feedback(data):
            return _fallback_mock_feedback()
        return data
    except Exception:
        return _fallback_mock_feedback()


def extract_mock_rating(feedback: dict) -> str:
    """从 analyze_mock_answer 的返回 dict 中提取评级。

    Returns:
        "优秀" / "良好" / "一般" / "待改进" 之一；
        匹配失败返回 "一般"。
    """
    return feedback.get("grade", "一般")


def analyze_summary(pairs_with_feedback: list[dict], job_direction: str) -> str:
    """对全部轮次调用 DeepSeek 生成整体复盘总结。

    Args:
        pairs_with_feedback: 每轮数据列表，含 index/question/answer/feedback。
        job_direction: 应聘岗位方向。

    Returns:
        AI 生成的总结文本；调用失败时返回友好错误提示。
    """
    prompt = build_summary_prompt(pairs_with_feedback, job_direction)
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=_API_TIMEOUT,
        )
        return response.choices[0].message.content or ""
    except ValueError as e:
        return f"[配置错误] {e}"
    except OpenAIError as e:
        return f"[API 调用失败] {e}"
    except Exception as e:
        if _is_timeout(e):
            return "[API超时] DeepSeek 响应超时，请稍后重试"
        return f"[未知错误] {e}"


def analyze_summary_stream(
    pairs_with_feedback: list[dict],
    job_direction: str,
):
    """
    流式版整体复盘总结，返回 generator，逐块 yield str。
    调用方负责拼接和展示。
    失败时 yield 一个错误提示字符串后结束。
    """
    prompt = build_summary_prompt(pairs_with_feedback, job_direction)
    try:
        client = _get_client()
        with client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=_API_TIMEOUT,
            stream=True,
        ) as stream:
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
    except Exception as e:
        err = str(e)
        if _is_timeout(e):
            yield "[API超时] 总结生成超时，请重试"
        else:
            yield f"[生成失败] {err}"


def _fallback_groups(pairs: list[dict]) -> list[dict]:
    """降级分组：每轮单独一组。"""
    return [{"topic": f"第{p['index']}轮", "turns": [p["index"]]} for p in pairs]


def _strip_markdown_fence(text: str) -> str:
    """去除 LLM 返回的 markdown 代码块包裹（```json ... ``` 或 ``` ... ```）。"""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _validate_groups(data: object) -> bool:
    """验证分组 JSON 结构：list，每个元素含 topic(str) 和 turns(list[int])。"""
    if not isinstance(data, list):
        return False
    for item in data:
        if not isinstance(item, dict):
            return False
        if not isinstance(item.get("topic"), str):
            return False
        turns = item.get("turns")
        if not isinstance(turns, list) or not all(isinstance(t, int) for t in turns):
            return False
    return True


def group_turns(pairs: list[dict]) -> list[dict]:
    """调用 DeepSeek 对问题列表进行话题分组。

    Args:
        pairs: [{"index": 1, "question": "..."}, ...]

    Returns:
        [{"topic": "话题名称", "turns": [1, 2]}, ...]
        调用或解析失败时返回降级分组（每轮单独一组）。
    """
    prompt = build_grouping_prompt(pairs)
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=_API_TIMEOUT,
        )
        raw = response.choices[0].message.content or ""
        cleaned = _strip_markdown_fence(raw)
        data = json.loads(cleaned)
        if not _validate_groups(data):
            return _fallback_groups(pairs)
        return data
    except Exception as e:
        return _fallback_groups(pairs)


_SCORE_KEYS = {
    "star_completeness", "technical_depth", "logical_clarity",
    "proactiveness", "result_orientation"
}


def _validate_scores(data: object) -> bool:
    """验证评分 JSON 结构：dict，含全部5个 key，每个 key 对应 score(1-10 int) 和 reason(str)。"""
    if not isinstance(data, dict):
        return False
    if not _SCORE_KEYS.issubset(data.keys()):
        return False
    for key in _SCORE_KEYS:
        item = data[key]
        if not isinstance(item, dict):
            return False
        score = item.get("score")
        reason = item.get("reason")
        if not isinstance(score, int) or not (1 <= score <= 10):
            return False
        if not isinstance(reason, str):
            return False
    return True


def score_session(summary: str) -> dict | None:
    """根据整体复盘总结调用 DeepSeek 对5个维度打分。

    Args:
        summary: 整体复盘总结文本（来自 analyze_summary 的输出）。

    Returns:
        {"star_completeness": {"score": 6, "reason": "..."}, ...}
        验证失败或 API 失败返回 None，不影响主流程。
    """
    prompt = build_scoring_prompt(summary)
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=_API_TIMEOUT,
        )
        raw = response.choices[0].message.content or ""
        cleaned = _strip_markdown_fence(raw)
        data = json.loads(cleaned)
        if not _validate_scores(data):
            return None
        return data
    except Exception:
        return None


def _validate_practice_plan(data: object) -> bool:
    """验证练习计划 JSON 结构。"""
    if not isinstance(data, dict):
        return False
    if not isinstance(data.get("summary"), str):
        return False
    plans = data.get("plans")
    if not isinstance(plans, list):
        return False

    required_keys = {
        "dimension",
        "label",
        "score",
        "diagnosis",
        "focus_topics",
        "action",
    }
    for plan in plans:
        if not isinstance(plan, dict):
            return False
        if not required_keys.issubset(plan.keys()):
            return False
    return True


def generate_practice_plan(
    weak_dimensions: list[dict],
    questions_by_topic: dict[str, list[dict]],
    job_direction: str,
) -> dict | None:
    """根据弱项维度和未掌握题目生成练习计划。

    Returns:
        {"summary": "...", "plans": [...]}；验证失败或 API 失败返回 None。
    """
    prompt = build_practice_plan_prompt(
        weak_dimensions=weak_dimensions,
        questions_by_topic=questions_by_topic,
        job_direction=job_direction,
    )
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=_API_TIMEOUT,
        )
        raw = response.choices[0].message.content or ""
        cleaned = _strip_markdown_fence(raw)
        data = json.loads(cleaned)
        if not _validate_practice_plan(data):
            return None
        return data
    except Exception:
        return None
