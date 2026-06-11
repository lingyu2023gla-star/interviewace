"""Prompt builder for structured JSON preparation plans."""

from __future__ import annotations


_EMPTY_EVIDENCE_CONTEXT = "无可用历史证据。"


def build_structured_preparation_plan_prompt(
    user_goal: str,
    evidence_context: str,
    job_direction: str = "",
    plan_days: int = 7,
    daily_minutes: int = 60,
    max_tasks_per_day: int = 3,
) -> str:
    """Build a prompt that asks the LLM to return a strict JSON object."""
    clean_goal = user_goal.strip()
    if not clean_goal:
        raise ValueError("user_goal 不能为空")
    if plan_days <= 0:
        raise ValueError("plan_days 必须大于 0")
    if daily_minutes <= 0:
        raise ValueError("daily_minutes 必须大于 0")
    if max_tasks_per_day <= 0:
        raise ValueError("max_tasks_per_day 必须大于 0")

    clean_evidence_context = evidence_context.strip() or _EMPTY_EVIDENCE_CONTEXT

    return f"""\
你是技术面试准备教练，必须基于历史证据生成结构化 JSON 准备计划。

## 强约束

- 只输出 JSON，不要输出 Markdown、解释、寒暄或多余文本。
- JSON 必须符合下方指定 object 结构，不能缺少顶层字段。
- 所有历史表现判断必须引用 evidence_refs，例如 ["E1"]。可以接受 [E1] 形式的历史证据输入，但输出建议统一写 "E1"。
- 如果历史证据不足，必须写“历史证据不足”，不能编造候选人没有展示过的能力、项目经历或面试表现。
- 可以建议下次主动展示，但不能写成候选人已经做到。
- 如果【历史证据】是“无可用历史证据。”，不要引用不存在的 E1，不要生成具体历史表现判断。
- daily_plan 必须包含 {plan_days} 天。
- 每天 tasks 数量不能超过 {max_tasks_per_day}。
- 每天 tasks 的 estimated_minutes 总和应围绕 {daily_minutes} 分钟。
- risk_warnings 不超过 3 条。
- question_templates 输出 2-3 条。
- abilities_to_show 输出 2-5 条。

## 输入

【用户目标】
{clean_goal}

【目标岗位方向】
{job_direction}

【计划天数】
{plan_days}

【每日可投入时间】
{daily_minutes}

【每日最多任务数】
{max_tasks_per_day}

【历史证据】
{clean_evidence_context}

## 必须输出如下 JSON object 结构

{{
  "summary": "用 1-3 句话总结准备重点；如果没有历史证据，必须写历史证据不足。",
  "evidence_based_judgments": [
    {{
      "type": "strength | weakness | insufficient_evidence | coverage_gap",
      "content": "基于历史证据的判断，或说明历史证据不足。",
      "evidence_refs": ["E1"]
    }}
  ],
  "daily_plan": [
    {{
      "day": 1,
      "goal": "当天准备目标",
      "tasks": [
        {{
          "task": "具体任务，不要写空泛表述",
          "estimated_minutes": 30,
          "output": "当天应产出的材料或话术",
          "evidence_refs": ["E1"]
        }}
      ]
    }}
  ],
  "question_templates": [
    {{
      "question": "最值得准备的问题",
      "answer_goal": "回答目标",
      "answer_structure": ["先给结论", "解释技术原因", "结合项目证据", "说明取舍", "说明结果或下一步"],
      "sample_answer": "自然、真实的示例回答；不能编造未做过的经历。",
      "evidence_refs": ["E1"]
    }}
  ],
  "abilities_to_show": [
    {{
      "ability": "需要主动展示的能力",
      "why_needed": "为什么目标岗位可能需要",
      "current_evidence_status": "历史证据不足 | 部分证据支持 | 已有证据支持但需要加强",
      "how_to_show_next_time": "下次如何主动展示"
    }}
  ],
  "risk_warnings": [
    {{
      "risk": "不能过度包装的点",
      "reason": "为什么不能这样说；如果依据不足，写历史证据不足。",
      "evidence_refs": ["E1"]
    }}
  ],
  "metadata": {{
    "user_goal": "{clean_goal}",
    "job_direction": "{job_direction}",
    "plan_days": {plan_days},
    "daily_minutes": {daily_minutes},
    "max_tasks_per_day": {max_tasks_per_day}
  }}
}}
"""
