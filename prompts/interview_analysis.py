"""
prompts/interview_analysis.py — 面试复盘分析 Prompt 模板管理

注意：这是产品核心，不要随意修改模板结构。
迭代时在修改处注释说明改动原因。
"""

import json

from jinja2 import Environment, StrictUndefined

from prompts.dimensions import DiagnosisDimension, get_diagnosis_dimensions

# ── Prompt 模板常量 ────────────────────────────────────────────────────────────
# 基于 STAR 面试法，围绕「知道哪错了 → 知道怎么改 → 知道怎么练」闭环设计。

ANALYSIS_PROMPT_TEMPLATE = """\
你是一个专业的面试复盘教练，擅长使用 STAR 面试法对候选人的回答进行深度分析。

## 你的任务
对以下面试问答记录进行结构化复盘分析，帮助候选人理解自己的表现并给出精准的改进建议。

## 分析前置说明
1. 本次面试内容围绕 AI 行业展开（AI 应用开发、大模型、Agent 架构等方向）
2. 转写文本来自语音识别，可能存在以下错误，分析时请自动修正理解，不要将其列为候选人的表达问题：
   - 同音字/近音字错误（如「a证」=「Agent」、「a政策」=「Agent」、「促」=「Tool」等）
   - 专业术语被识别为无关词汇（如「长链」=「LangChain」、「Gs」=「Good or Same」）
   - 数字和英文混淆
   - **重要：以上识别错误不得出现在分析报告中，不得据此评价候选人的专业性或表达能力**
3. 忽略候选人回答中的口语化表达（如「然后」「这样的」「就是说」「对吧」等填充词），只针对实质内容进行分析
4. 分析重心放在 AI 技术理解深度、架构设计能力、实际落地经验上

## 面试记录
【面试问题】：{question}
【候选人回答】：{answer}
【岗位方向】：{job_direction}

## 分析维度

### 1. STAR 完整度检查
逐项判断候选人回答是否包含以下要素，并给出该要素的质量评价：
- Situation（背景）：是否清晰交代了场景和前提？
- Task（任务）：是否明确说明了自己的职责和目标？
- Action（行动）：是否具体描述了做了什么？行动是否有层次？
- Result（结果）：是否给出了可量化或可验证的结果？

### 2. 回答准确性
- 是否有明显的事实性错误或表述偏差？
- 回答是否真正响应了问题的核心考察点？
- 有无逻辑断裂或前后矛盾的地方？

### 3. 整体逻辑评估
- 表达是否清晰流畅？
- 重点是否突出，有无冗余信息干扰？
- 整体论述的说服力如何？

### 4. 等级判定
根据以上分析，判断这个回答属于哪个等级：
- 优秀：STAR 完整，逻辑清晰，结果具体，直接响应考察点
- 良好：大部分要素具备，有小瑕疵但不影响整体
- 一般：要素缺失明显，或逻辑存在问题
- 待改进：回答偏题、要素严重缺失或存在明显错误

### 5. 参考答案框架
给出一个针对这道题的优秀回答框架：
- 建议的 STAR 结构拆解
- 关键信息点清单
- 示范表达方式（1-2 句核心句式）

### 6. 改进行动清单
给出 3 条具体可执行的改进建议，严格按照以下格式输出：
- 【问题】具体指出哪里不足
- 【改进】下次应该怎么说
- 【练习】如何针对性练习这个点

## 输出格式
只输出 JSON，不输出任何其他内容（不要有说明文字、markdown 代码块、注释）。
格式：
{{
  "star_completeness": {{
    "situation": "对 Situation 要素的评价",
    "task": "对 Task 要素的评价",
    "action": "对 Action 要素的评价",
    "result": "对 Result 要素的评价"
  }},
  "accuracy": "回答准确性评价（1-2句）",
  "logic": "整体逻辑评估（1-2句）",
  "grade": "优秀|良好|一般|待改进",
  "reference_answer": "参考答案框架（建议的STAR结构拆解+关键信息点+示范句式）",
  "improvements": [
    {{"problem": "问题描述", "suggestion": "改进建议", "practice": "练习方法"}},
    {{"problem": "问题描述", "suggestion": "改进建议", "practice": "练习方法"}},
    {{"problem": "问题描述", "suggestion": "改进建议", "practice": "练习方法"}}
  ]
}}\
"""

MOCK_FEEDBACK_PROMPT_TEMPLATE = """\
你是一个 AI 行业面试反馈助手。

## 前置说明
1. 本次面试内容围绕 AI 行业展开。
2. 忽略候选人回答中的口语化表达，只看实质内容。
3. 不需要做完整 STAR 分析，只抓最关键的点。

## 输入
【面试问题】：{question}
【候选人回答】：{answer}
【岗位方向】：{job_direction}

## 输出格式
只输出 JSON，不输出任何其他内容（不要有说明文字、markdown 代码块、注释）。
格式：
{{
  "highlight": "亮点（1-2句）",
  "problem": "主要问题（1-2句，不超过两点）",
  "suggestion": "建议（1句，下次可以怎么说）",
  "grade": "优秀|良好|一般|待改进"
}}\
"""

SUMMARY_PROMPT_TEMPLATE = """\
你是一个专业的面试复盘教练，擅长从多轮面试问答中提炼整体表现规律。

## 分析前置说明
1. 本次面试内容围绕 AI 行业展开（AI 应用开发、大模型、Agent 架构等方向）
2. 转写文本来自语音识别，可能存在同音字/近音字错误、专业术语识别偏差、数字和英文混淆等问题，分析时请自动修正理解，不要将其列为候选人的表达问题，也不得出现在分析报告中
3. 忽略候选人回答中的口语化表达，只针对实质内容进行分析
4. 分析重心放在 AI 技术理解深度、架构设计能力、实际落地经验上

## 面试信息
【岗位方向】：{job_direction}
【话题数】：{total_rounds} 个

## 各话题问答与反馈
{rounds_text}

## 输出结构
请严格按以下结构输出，每个部分单独成块：

### 1. 整体表现评估
（1段话，跨话题综合判断候选人的整体水平）

### 2. 三大核心问题
对每个问题按以下格式输出：
- **问题名称**：
- **具体表现**：
- **出现位置**：「话题名称」
- **改进方向**：

### 3. 亮点
候选人表现好的地方，每条注明出现在哪个话题，格式：「话题名称」。

### 4. 优先改进建议
按影响力从高到低排序，给出 3 条具体可执行的建议。\
"""


def build_analysis_prompt(question: str, answer: str, job_direction: str) -> str:
    """将面试问答填入分析 Prompt 模板，返回完整 prompt 字符串。

    Args:
        question: 面试官提出的问题。
        answer: 候选人的回答。
        job_direction: 应聘岗位方向，如「后端开发」「产品经理」。

    Returns:
        填充完毕的 prompt 字符串，可直接传给 LLM。
    """
    return ANALYSIS_PROMPT_TEMPLATE.format(
        question=question,
        answer=answer,
        job_direction=job_direction,
    )


def build_mock_feedback_prompt(question: str, answer: str, job_direction: str) -> str:
    """将模拟面试单轮问答填入简短反馈 Prompt 模板。

    Args:
        question: 面试官提出的问题。
        answer: 候选人的回答。
        job_direction: 应聘岗位方向。

    Returns:
        填充完毕的 prompt 字符串，可直接传给 LLM。
    """
    return MOCK_FEEDBACK_PROMPT_TEMPLATE.format(
        question=question,
        answer=answer,
        job_direction=job_direction,
    )


def build_summary_prompt(pairs_with_feedback: list[dict], job_direction: str) -> str:
    """将多轮问答及单轮反馈填入总结 Prompt 模板。

    Args:
        pairs_with_feedback: 每轮数据，结构为
            [{"index": 1, "topic": "...", "question": "...", "answer": "...", "feedback": "..."}, ...]
            topic 字段可选，有则用话题名作标题，无则降级为「第 X 轮」。
        job_direction: 应聘岗位方向。

    Returns:
        填充完毕的 prompt 字符串，可直接传给 LLM。
    """
    rounds_lines = []
    for item in pairs_with_feedback:
        topic = item.get("topic", "")
        header = f"--- 话题：{topic} ---" if topic else f"--- 第 {item['index']} 轮 ---"
        rounds_lines.append(
            f"{header}\n"
            f"【问题】{item['question']}\n"
            f"【回答】{item['answer']}\n"
            f"【反馈摘要】{item['feedback'][:600]}{'…' if len(item['feedback']) > 600 else ''}"
        )
    rounds_text = "\n\n".join(rounds_lines)
    return SUMMARY_PROMPT_TEMPLATE.format(
        job_direction=job_direction,
        total_rounds=len(pairs_with_feedback),
        rounds_text=rounds_text,
    )


GROUPING_PROMPT_TEMPLATE = """\
你是一个面试分析助手。

## 前置说明
1. 本次面试内容围绕 AI 行业展开（AI 应用开发、大模型、Agent 架构等方向）
2. 问题文本来自语音识别转写，可能存在同音字/近音字错误、专业术语识别偏差等问题，请自动修正理解

## 任务
将以下面试问题按话题分组。

## 问题列表
{questions_text}

## 输出要求
- 只输出 JSON，不输出任何其他内容（不要有说明文字、markdown 代码块、注释）
- 每个轮次只能属于一个组，所有轮次必须被分配
- 格式：
[{{"topic": "话题名称", "turns": [1, 2]}}, ...]\
"""


def build_grouping_prompt(pairs: list[dict]) -> str:
    """将问题列表填入话题分组 Prompt 模板。

    Args:
        pairs: 问题列表，每个 dict 含 index 和 question，如
            [{"index": 1, "question": "请介绍你自己"}, ...]

    Returns:
        填充完毕的 prompt 字符串，可直接传给 LLM。
    """
    questions_lines = [f"第 {p['index']} 轮：{p['question']}" for p in pairs]
    questions_text = "\n".join(questions_lines)
    return GROUPING_PROMPT_TEMPLATE.format(questions_text=questions_text)


FULL_CONTEXT_ANALYSIS_PROMPT = """\
你是一个技术面试复盘教练，专注于「大模型应用工程 / AI 应用后端 / Agent / RAG / 应用算法」方向。

请基于完整面试转写，输出高密度、可执行的技术面试诊断。
不要写泛泛总结，不要输出不可靠的综合评分，不要做空泛鼓励。

## 分析原则

1. 转写来自语音识别，可能有专业术语识别错误。请自动修正明显偏差，不要把语音识别错误归咎于候选人。
2. 只评价技术岗位相关表现，重点看技术理解、项目可信度、工程意识和表达结构。
3. 必须区分：
   - 能力不足：回答错误、过浅、混乱或缺少实践细节
   - 证据不足：本场没有问到，或候选人没有展开
   - 覆盖缺口：目标岗位需要该能力，但本场没有充分展示
4. 未被问到的能力不要强行打低分，标记为「未验证 / N/A」。
5. 如果候选人只堆技术名词，但没有讲机制、边界、取舍、项目落地或验证方式，应指出为「概念知道，但深度不足」。
6. 所有建议必须具体到“下次应该怎么说”或“项目中应该补什么证据”。

## 岗位方向

{{ job_direction }}

请根据岗位方向动态调整关注重点：

- 偏后端大模型应用：API、数据库、Redis、Celery、任务状态、异常处理、测试、部署、LLM 稳定性。
- 偏 Agent / RAG：Orchestrator、Tool、状态流、RAG 召回/重排/引用、上下文组装、输出结构化。
- 偏应用算法：Prompt、RAG 效果优化、微调、数据构造、评估集、指标体系、效果对比。

## 完整面试转写

{{ full_text }}

## 输出格式

请严格只输出以下 2 个部分。

# 1. 能力诊断表

请使用表格：

| 维度 | 覆盖状态 | 证据强度 | 分数 | 诊断 | 具体建议 |
|---|---|---|---:|---|---|

维度固定如下：

{% for dimension in dimensions -%}
{{ loop.index }}. {{ dimension.name }}
   - 关注点：{{ dimension.focus }}
{% endfor %}

规则：

- 覆盖状态只能是：已覆盖 / 部分覆盖 / 未验证
- 证据强度只能是：强 / 中 / 弱 / 无
- 已覆盖或部分覆盖时，可以给 0-10 分
- 未验证时，分数写 N/A，不要强行扣分
- 诊断必须基于本场面试证据
- 具体建议必须说明下一次应该如何补强

# 2. 具体改进建议

只列出最值得改的 {{ max_suggestions }} 个问题。
不要泛泛而谈，每条都要能直接用于下一次面试准备。

每条按以下格式输出：

## 建议 X：标题

- 暴露的问题：
- 为什么会影响面试结果：
- 下次应该怎么说：
- 项目中应该补什么证据：
- 面试官可能追问：
"""


def build_full_context_analysis_prompt(
    full_text: str,
    job_direction: str = "",
    dimension_profile: str = "llm_app",
    dimensions: list[DiagnosisDimension] | None = None,
    max_suggestions: int = 5,
) -> str:
    """将完整面试文本和诊断维度渲染为全量上下文分析 Prompt。"""
    selected_dimensions = dimensions
    if selected_dimensions is None:
        selected_dimensions = get_diagnosis_dimensions(dimension_profile)
    if not selected_dimensions:
        raise ValueError("能力诊断维度不能为空")

    template = Environment(undefined=StrictUndefined).from_string(FULL_CONTEXT_ANALYSIS_PROMPT)
    return template.render(
        full_text=full_text,
        job_direction=job_direction,
        dimensions=selected_dimensions,
        max_suggestions=max_suggestions,
    )


SCORING_PROMPT_TEMPLATE = """\
你是一个专业的面试评估专家。

## 前置说明
1. 本次面试内容围绕 AI 行业展开（AI 应用开发、大模型、Agent 架构等方向）
2. 以下总结文本来自语音识别转写，可能存在同音字/近音字错误、专业术语识别偏差等问题，请自动修正理解
3. 忽略口语化表达，只针对实质内容评分

## 面试复盘总结
{summary}

## 评分任务
根据以上总结，对候选人在以下 5 个维度各打 1-10 分，并附一句话说明理由：
- star_completeness：STAR 结构完整度（是否清晰交代背景、任务、行动、结果）
- technical_depth：AI 技术理解深度（对大模型、Agent、工程落地的理解程度）
- logical_clarity：表达逻辑清晰度（论述是否有条理、重点是否突出）
- proactiveness：主动性与行动导向（是否展现出主动推动事情的意愿和能力）
- result_orientation：结果导向与量化能力（是否给出可量化或可验证的结果）

## 输出要求
只输出 JSON，不输出任何其他内容（不要有说明文字、markdown 代码块、注释）。
格式：
{{
  "star_completeness": {{"score": 6, "reason": "一句话说明"}},
  "technical_depth": {{"score": 7, "reason": "一句话说明"}},
  "logical_clarity": {{"score": 5, "reason": "一句话说明"}},
  "proactiveness": {{"score": 4, "reason": "一句话说明"}},
  "result_orientation": {{"score": 5, "reason": "一句话说明"}}
}}\
"""


def build_scoring_prompt(summary: str) -> str:
    """将整体复盘总结填入评分 Prompt 模板。

    Args:
        summary: 整体复盘总结文本（来自 analyze_summary 的输出）。

    Returns:
        填充完毕的 prompt 字符串，可直接传给 LLM。
    """
    return SCORING_PROMPT_TEMPLATE.format(summary=summary)


PRACTICE_PLAN_PROMPT_TEMPLATE = """\
你是一个 AI 行业面试训练教练，擅长根据历史评分数据制定定向强化计划。

## 前置说明
本次任务面向 AI 行业面试，请根据候选人的历史评分弱项和题库中可练习题目，制定可执行的强化计划。

## 输入
【目标岗位】：{job_direction}

【弱项维度（含平均分）】：
{weak_dimensions_text}

【可练习题目（按话题分组）】：
{questions_by_topic_text}

## 输出要求
- 按维度输出强化计划。
- plans 按 score 升序排列，最弱的维度排最前。
- focus_topics 优先选择可练习题目中最相关的话题。
- 只输出 JSON，不输出任何其他内容（不要有说明文字、markdown 代码块、注释）。

格式：
{{
  "summary": "一句话总体建议",
  "plans": [
    {{
      "dimension": "维度英文key",
      "label": "维度中文名",
      "score": 4.2,
      "diagnosis": "该维度的问题诊断（1-2句）",
      "focus_topics": ["话题名1", "话题名2"],
      "action": "具体练习方法（1-2句）"
    }}
  ]
}}\
"""


def build_practice_plan_prompt(
    weak_dimensions: list[dict],
    questions_by_topic: dict[str, list[dict]],
    job_direction: str,
) -> str:
    """将弱项维度和可练习题目填入练习计划 Prompt 模板。

    Args:
        weak_dimensions: 弱项维度列表，含 dimension/label/avg_score。
        questions_by_topic: 按话题分组的未掌握题目。
        job_direction: 目标岗位方向。

    Returns:
        填充完毕的 prompt 字符串，可直接传给 LLM。
    """
    return PRACTICE_PLAN_PROMPT_TEMPLATE.format(
        job_direction=job_direction,
        weak_dimensions_text=json.dumps(weak_dimensions, ensure_ascii=False, indent=2),
        questions_by_topic_text=json.dumps(questions_by_topic, ensure_ascii=False, indent=2),
    )
