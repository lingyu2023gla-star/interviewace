from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from agent.schemas import ToolResult
from core.parser import parse_text
from core.analyzer import (
    group_turns,
    analyze_turn,
    analyze_summary,
    score_session,
    extract_questions,
)
from core.storage import save_session, add_question

_MIN_ANSWER_LEN = 20


def _turn_to_dict(turn) -> dict:
    return {
        "speaker": turn.speaker,
        "timestamp": turn.timestamp,
        "content": turn.content,
    }


def _build_pairs(turns: list[dict]) -> list[dict]:
    pairs: list[dict] = []
    i = 0
    while i < len(turns):
        turn = turns[i]
        if turn["speaker"] == "interviewer":
            question_parts = [turn["content"]]
            j = i + 1
            while j < len(turns) and turns[j]["speaker"] == "interviewer":
                question_parts.append(turns[j]["content"])
                j += 1

            question = "\n".join(question_parts)
            while j < len(turns) and turns[j]["speaker"] != "candidate":
                j += 1

            if j < len(turns):
                answer = turns[j]["content"]
                if len(answer) >= _MIN_ANSWER_LEN:
                    pairs.append({
                        "index": len(pairs) + 1,
                        "question": question,
                        "answer": answer,
                    })
                i = j + 1
                continue
        i += 1
    return pairs


def tool_parse_interview(text: str, role_map: dict | None = None) -> ToolResult:
    try:
        session = parse_text(text, role_map=role_map)
        turns = [_turn_to_dict(turn) for turn in session.turns]
        pairs = _build_pairs(turns)
        return ToolResult(
            success=True,
            data={
                "title": session.title,
                "turns": turns,
                "candidate_turns": session.candidate_turns,
                "pairs": pairs,
            },
        )
    except Exception as e:
        return ToolResult(success=False, data=None, error=str(e))


def tool_group_topics(pairs: list[dict]) -> ToolResult:
    try:
        question_pairs = [
            {"index": item["index"], "question": item["question"]}
            for item in pairs
        ]
        groups = group_turns(question_pairs)
        return ToolResult(success=True, data={"groups": groups})
    except Exception as e:
        return ToolResult(success=False, data=None, error=str(e))


def _dict_to_feedback_text(feedback: dict) -> str:
    """将结构化 feedback dict 转为可读文本，供展示和 summary prompt 使用。"""
    if "_error" in feedback:
        return f"[分析失败] {feedback['_error']}"

    star = feedback.get("star_completeness", {})
    lines = []
    lines.append("### STAR 完整度")
    lines.append(f"- Situation：{star.get('situation', '')}")
    lines.append(f"- Task：{star.get('task', '')}")
    lines.append(f"- Action：{star.get('action', '')}")
    lines.append(f"- Result：{star.get('result', '')}")
    lines.append(f"\n### 准确性\n{feedback.get('accuracy', '')}")
    lines.append(f"\n### 逻辑\n{feedback.get('logic', '')}")
    lines.append(f"\n### 等级判定\n{feedback.get('grade', '')}")
    lines.append(f"\n### 参考答案框架\n{feedback.get('reference_answer', '')}")

    improvements = feedback.get("improvements", [])
    if improvements:
        lines.append("\n### 改进行动清单")
        for imp in improvements:
            lines.append(f"- 【问题】{imp.get('problem', '')}")
            lines.append(f"  【改进】{imp.get('suggestion', '')}")
            lines.append(f"  【练习】{imp.get('practice', '')}")

    return "\n".join(lines)


def _analyze_single_group(
    group_idx: int,
    group: dict,
    pairs: list[dict],
    job_direction: str,
) -> dict:
    """分析单个话题组，返回 feedback dict，供并行调用。"""
    topic = group["topic"]
    turn_indices = group["turns"]
    group_pairs = [
        (pairs[i - 1]["question"], pairs[i - 1]["answer"])
        for i in turn_indices
        if 0 < i <= len(pairs)
    ]
    merged_question = "\n\n".join(
        f"[{i}] {q}" for i, (q, _) in zip(turn_indices, group_pairs)
    )
    merged_answer = "\n\n".join(
        f"[{i}] {a}" for i, (_, a) in zip(turn_indices, group_pairs)
    )
    feedback_dict = analyze_turn(merged_question, merged_answer, job_direction)
    feedback_text = _dict_to_feedback_text(feedback_dict)
    return {
        "index": group_idx + 1,
        "topic": topic,
        "question": merged_question,
        "answer": merged_answer,
        "feedback": feedback_text,
        "feedback_dict": feedback_dict,
    }


def tool_analyze_topics(groups: list[dict], pairs: list[dict], job_direction: str) -> ToolResult:
    """
    循环调用 analyze_turn，返回：
    {"feedbacks": [{"index":1,"topic":"...","question":"...","answer":"...","feedback":"..."}]}
    """
    try:
        results: dict[int, dict] = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_idx = {
                executor.submit(
                    _analyze_single_group, idx, group, pairs, job_direction
                ): idx
                for idx, group in enumerate(groups)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                results[idx] = future.result()  # 异常会在这里抛出
        # 按原始顺序排列
        feedbacks = [results[i] for i in range(len(groups))]
        return ToolResult(success=True, data={"feedbacks": feedbacks})
    except Exception as e:
        return ToolResult(success=False, data=None, error=str(e))


def tool_generate_summary(feedbacks: list[dict], job_direction: str) -> ToolResult:
    try:
        summary = analyze_summary(feedbacks, job_direction)
        return ToolResult(success=True, data={"summary": summary})
    except Exception as e:
        return ToolResult(success=False, data=None, error=str(e))


def tool_score_performance(summary: str) -> ToolResult:
    try:
        scores = score_session(summary)
        return ToolResult(success=True, data={"scores": scores})
    except Exception as e:
        return ToolResult(success=False, data=None, error=str(e))


def tool_save_results(
    title: str,
    job_direction: str,
    summary: str,
    feedbacks: list[dict],
    scores: dict | None,
    session_id_holder: list,
) -> ToolResult:
    """保存会话并自动沉淀题库，返回 {"session_id": int, "questions_saved": int}"""
    try:
        session_id = save_session(
            title=title,
            job_direction=job_direction,
            summary=summary,
            turns=feedbacks,
            scores=scores,
        )
        session_id_holder.append(session_id)

        questions_saved = 0
        for item in feedbacks:
            extracted = extract_questions(
                topic=item.get("topic", ""),
                question=item["question"],
                feedback=item.get("feedback_dict", {}),
            )
            if extracted is None:
                continue
            try:
                add_question(
                    source_session_id=session_id,
                    topic=extracted["topic"],
                    question=extracted["question"],
                    reference_answer=extracted["reference_answer"],
                    difficulty=extracted["difficulty"],
                )
                questions_saved += 1
            except Exception:
                pass

        return ToolResult(
            success=True,
            data={"session_id": session_id, "questions_saved": questions_saved},
        )
    except Exception as e:
        return ToolResult(success=False, data=None, error=str(e))
