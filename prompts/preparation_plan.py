"""Prompt builder for evidence-based interview preparation plans."""

from __future__ import annotations


_EMPTY_EVIDENCE_CONTEXT = "无可用历史证据。"


def build_preparation_plan_prompt(
    user_goal: str,
    evidence_context: str,
    job_direction: str = "",
    plan_days: int = 7,
    daily_minutes: int = 60,
    max_tasks_per_day: int = 3,
) -> str:
    """Build a prompt for an evidence-based interview preparation plan."""
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
你是技术面试准备教练，擅长基于候选人的历史面试证据，制定下一阶段可执行准备计划。

## 强约束

- 只能基于【历史证据】判断候选人过去表现。
- 所有历史表现判断必须引用证据编号，例如 [E1]。
- 如果证据不足，必须明确写“历史证据不足”。
- 可以给出“建议主动展示”的能力，但不能把建议写成候选人已经做到。
- 不能编造候选人没有展示过的项目经历、技术能力或面试表现。
- 计划必须可执行，不能只写“加强学习”“提升表达”这种空泛建议。
- 每天任务数量不能超过 {max_tasks_per_day}。
- 每天总投入时间应围绕 {daily_minutes} 分钟设计。
- 如果【历史证据】是“无可用历史证据。”，不要生成任何关于候选人历史表现的判断，不要引用不存在的 [E1]，只根据用户目标、岗位方向、计划天数和每日时间生成通用准备计划。

## 输入

【用户目标】
{clean_goal}

【目标岗位方向】
{job_direction}

【计划天数】
{plan_days} 天

【每日可投入时间】
{daily_minutes} 分钟

【每日最多任务数】
{max_tasks_per_day}

【历史证据】
{clean_evidence_context}

## 输出格式

# 1. 准备重点判断

输出 3-5 条。
要求：
- 如果判断来自历史证据，必须引用 [E1]。
- 如果没有历史证据支撑，必须写“历史证据不足”。
- 需要区分已有证据支持的优势、已有证据暴露的问题、证据不足但目标岗位建议主动展示的能力。
- 如果没有可用历史证据，必须说明：当前没有历史证据可引用，建议先完成一次面试复盘或导入历史记录。

# 2. {plan_days} 天准备计划

使用表格：

| 天数 | 目标 | 任务 | 预计时间 | 产出物 | 对应证据 |
|---|---|---|---|---|---|

规则：
- 每天任务数不能超过 {max_tasks_per_day}。
- 每天预计总时间应接近 {daily_minutes} 分钟。
- 任务必须具体，例如整理 Agent Orchestrator 回答模板、补充 RAG 已实现 / 未实现边界说明、准备 Prompt 防幻觉案例、写出 Redis / Celery 未验证能力的主动展示话术。
- 对应证据列必须写 [E1] / [E2] / 历史证据不足。

# 3. 重点问题回答模板

选择 2-3 个最值得准备的问题。

每个问题按以下格式：

## 问题 X：问题标题

- 回答目标：
- 建议回答结构：
  1. 先给结论
  2. 解释技术原因
  3. 结合项目证据
  4. 说明取舍
  5. 说明结果或下一步
- 示例回答：
- 对应证据：

要求：
- 示例回答必须自然、真实。
- 不能编造候选人没有做过的经历。
- 如果某能力只是规划中，必须明确说“当前还在规划 / 尚未完整实现”。

# 4. 需要主动展示但历史证据不足的能力

使用表格：

| 能力 | 为什么目标岗位可能需要 | 当前证据状态 | 下次如何主动展示 |
|---|---|---|---|

要求：
- 当前证据状态只能写：历史证据不足 / 部分证据支持 / 已有证据支持但需要加强。
- 不能写成能力差，除非历史证据明确显示回答错误或严重不足。

# 5. 过度包装风险提醒

列出 3 条以内。
重点提醒：
- 哪些能力不能说成已经完成。
- 哪些能力只能说成规划中或待补强。
- 哪些表达容易被面试官追问。
"""
