"""能力诊断维度配置。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiagnosisDimension:
    """单个面试能力诊断维度。"""

    key: str
    name: str
    focus: str


DEFAULT_LLM_APP_DIMENSIONS = [
    DiagnosisDimension(
        key="technical_concept_accuracy",
        name="技术概念准确性",
        focus="判断候选人是否把核心技术概念讲对，例如 Agent、RAG、Prompt、Redis、Celery、微调、评估等。",
    ),
    DiagnosisDimension(
        key="technical_depth",
        name="技术深度",
        focus="判断候选人是否能讲清机制、边界、原理、限制和实践细节，而不是只停留在名词解释。",
    ),
    DiagnosisDimension(
        key="backend_engineering",
        name="后端工程基础",
        focus="关注 FastAPI / Django、API 设计、MySQL、Redis、Celery / RabbitMQ、Docker / Linux、测试、部署等能力。",
    ),
    DiagnosisDimension(
        key="system_architecture",
        name="系统架构能力",
        focus="关注候选人是否能把系统拆成接口层、任务层、存储层、缓存层、Agent 编排层、测试层等。",
    ),
    DiagnosisDimension(
        key="llm_application",
        name="大模型应用理解",
        focus="关注 LLM API、上下文窗口、输出结构化、模型失败、超时、重试、降级、成本和稳定性。",
    ),
    DiagnosisDimension(
        key="prompt_engineering",
        name="Prompt 工程能力",
        focus="关注任务目标定义、约束设计、格式控制、噪音处理、多轮迭代、失败样例优化。",
    ),
    DiagnosisDimension(
        key="agent_architecture",
        name="Agent 架构能力",
        focus="关注 Orchestrator、Tool、状态流、工具调用、错误处理、降级策略、可观测性、可测试性。",
    ),
    DiagnosisDimension(
        key="rag_capability",
        name="RAG 能力",
        focus="关注文档清洗、切分、向量化、召回、重排、引用、知识库更新、上下文拼接、幻觉控制。",
    ),
    DiagnosisDimension(
        key="finetuning_and_evaluation",
        name="微调与评估能力",
        focus="关注 SFT、LoRA、数据构造、训练样本、评估集、指标设计、Prompt vs 微调取舍、效果对比。",
    ),
    DiagnosisDimension(
        key="technical_tradeoff",
        name="技术取舍能力",
        focus="关注候选人是否能解释为什么这样设计，有哪些替代方案，当前阶段为什么不做复杂化。",
    ),
    DiagnosisDimension(
        key="debugging_and_reliability",
        name="问题定位与稳定性意识",
        focus="关注日志、异常处理、超时、重试、降级、边界条件、测试、线上问题排查。",
    ),
    DiagnosisDimension(
        key="communication_and_delivery",
        name="表达结构与交付感",
        focus="关注候选人是否先给结论、再解释原因、结合项目、说明取舍和结果，是否让面试官相信其能实际交付。",
    ),
]


DIMENSION_PROFILES = {
    "llm_app": DEFAULT_LLM_APP_DIMENSIONS,
}


def get_diagnosis_dimensions(profile: str = "llm_app") -> list[DiagnosisDimension]:
    """按 profile 获取能力诊断维度浅拷贝。"""
    if profile not in DIMENSION_PROFILES:
        available = ", ".join(sorted(DIMENSION_PROFILES))
        raise ValueError(f"未知能力维度 profile: {profile}。可用 profile: {available}")
    return list(DIMENSION_PROFILES[profile])
