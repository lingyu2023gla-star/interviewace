from __future__ import annotations

from agent.schemas import AgentContext, Intent, ToolResult
from agent.tools import (
    tool_parse_interview,
    tool_group_topics,
    tool_analyze_topics,
    tool_analyze_full_interview,
    tool_generate_summary,
    tool_score_performance,
    tool_save_results,
)


# ── 工具链声明 ────────────────────────────────────────────────────────────────

TOOL_CHAIN_ANALYZE_INTERVIEW = [
    "parse_interview",
    "group_topics",
    "analyze_topics",
    "generate_summary",
    "score_performance",
    "save_results",
]

TOOL_CHAIN_ANALYZE_FULL_CONTEXT = [
    "parse_interview",
    "build_full_interview_text",
    "analyze_full_interview",
    "generate_summary",
    "score_performance",
    "save_results",
]

# 降级策略
FALLBACK_STRATEGIES: dict[str, str] = {
    "group_topics": "every_turn_standalone",  # 分组失败 → 每轮独立
    "score_performance": "skip",              # 评分失败 → 跳过
    "generate_summary": "skip",               # 总结失败 → 跳过
    "analyze_topics": "retry_once",           # 分析失败 → 重试一次
}


# ── Orchestrator ──────────────────────────────────────────────────────────────

class InterviewOrchestrator:

    def run_analyze_interview(
        self,
        text: str,
        job_direction: str,
        title: str = "未命名面试",
        on_step: callable | None = None,
        role_map: dict | None = None,
        analysis_mode: str = "full_context",
    ) -> ToolResult:
        """
        执行 ANALYZE_INTERVIEW 完整链路。

        Args:
            text: 讯飞转写原始文本
            job_direction: 岗位方向
            title: 会话标题（来自文件名）
            on_step: 每步完成后的回调，签名 on_step(step_name: str, result: ToolResult)
                     供 Streamlit 实时更新进度
            role_map: 说话人角色映射，如 {"说话人1": "candidate", "说话人2": "interviewer"}
            analysis_mode: 分析模式，"topic" 走原话题分组链路，"full_context" 走全量上下文链路
        Returns:
            最终 ToolResult，data 结构：
            {
                "session_id": int,
                "feedbacks": [...],
                "summary": str,
                "scores": dict | None,
                "questions_saved": int,
            }
        """
        ctx = AgentContext(
            intent=Intent.ANALYZE_INTERVIEW,
            user_input={
                "text": text,
                "job_direction": job_direction,
                "title": title,
                "role_map": role_map,
                "analysis_mode": analysis_mode,
            },
            job_direction=job_direction,
        )

        if analysis_mode not in {"topic", "full_context"}:
            return ToolResult(
                success=False,
                data=None,
                error=f"不支持的分析模式：{analysis_mode}",
            )

        # Step 1: 解析
        result = tool_parse_interview(text, role_map=role_map)
        ctx.tool_results["parse_interview"] = result
        if on_step:
            on_step("parse_interview", result)
        if not result.success:
            return ToolResult(success=False, data=None, error=f"文件解析失败：{result.error}")

        pairs = result.data["pairs"]
        if not pairs:
            return ToolResult(success=False, data=None, error="未找到有效问答轮次")

        if analysis_mode == "topic":
            # Step 2: 话题分组
            result = tool_group_topics(pairs)
            if not result.success:
                # 降级：每轮独立
                groups = [{"topic": f"第{p['index']}轮", "turns": [p["index"]]} for p in pairs]
            else:
                groups = result.data["groups"]
            ctx.tool_results["group_topics"] = result
            if on_step:
                on_step("group_topics", result)

            # Step 3: 逐话题分析
            result = tool_analyze_topics(groups, pairs, job_direction)
            if not result.success:
                # 重试一次
                result = tool_analyze_topics(groups, pairs, job_direction)
            ctx.tool_results["analyze_topics"] = result
            if on_step:
                on_step("analyze_topics", result)
            if not result.success:
                return ToolResult(success=False, data=None, error=f"分析失败：{result.error}")

            feedbacks = result.data["feedbacks"]
        else:
            groups = [{"topic": "完整面试复盘", "turns": [p["index"] for p in pairs]}]
            result = tool_analyze_full_interview(ctx)
            ctx.tool_results["analyze_full_interview"] = result
            if on_step:
                on_step("analyze_full_interview", result)
            if not result.success:
                return ToolResult(success=False, data=None, error=f"全量上下文分析失败：{result.error}")

            feedbacks = result.data["analyses"]

        # Step 4: 整体总结
        result = tool_generate_summary(feedbacks, job_direction)
        ctx.tool_results["generate_summary"] = result
        if on_step:
            on_step("generate_summary", result)
        summary = result.data["summary"] if result.success else ""

        # Step 5: 能力评分
        result = tool_score_performance(summary) if summary else ToolResult(success=False, data=None, error="无总结，跳过评分")
        ctx.tool_results["score_performance"] = result
        if on_step:
            on_step("score_performance", result)
        scores = result.data["scores"] if result.success else None

        # Step 6: 保存
        session_id_holder: list[int] = []
        result = tool_save_results(
            title=title,
            job_direction=job_direction,
            summary=summary,
            feedbacks=feedbacks,
            scores=scores,
            session_id_holder=session_id_holder,
        )
        ctx.tool_results["save_results"] = result
        if on_step:
            on_step("save_results", result)

        session_id = session_id_holder[0] if session_id_holder else None
        questions_saved = result.data.get("questions_saved", 0) if result.success else 0

        return ToolResult(
            success=True,
            data={
                "session_id": session_id,
                "feedbacks": feedbacks,
                "summary": summary,
                "scores": scores,
                "questions_saved": questions_saved,
                "title": title,
                "groups_count": len(groups),
            },
        )


# 单例，供外部直接 import 使用
orchestrator = InterviewOrchestrator()
