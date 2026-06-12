"""Project pitch skill backed by retrievers, Evidence Context, and LLM text generation."""

from __future__ import annotations

from typing import Any

from core.analyzer import generate_text
from knowledge.context_builder import build_evidence_context
from knowledge.retrievers.factory import get_retriever
from preparation.evidence_validator import (
    EvidenceValidationResult,
    evidence_validation_result_to_dict,
    extract_evidence_refs_from_text,
    extract_valid_evidence_ids,
    validate_evidence_refs,
)
from skills.base import BaseSkill
from skills.schemas import SkillRequest, SkillResult, SkillSpec


SKILL_NAME = "project_pitch"


def _as_bool(value: Any) -> bool:
    """Convert common truthy values to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _as_str_list(value: Any) -> list[str]:
    """Return a clean string list from a list-like input."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _extract_markdown_sections(text: str) -> list[str]:
    """Extract top-level Markdown headings as lightweight section metadata."""
    sections = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                sections.append(title)
    return sections


def build_project_pitch_prompt(
    *,
    project_name: str,
    target_role: str,
    duration_minutes: int,
    language: str,
    focus_points: list[str],
    style: str,
    evidence_context: str,
) -> str:
    """Build an evidence-based project pitch prompt."""
    focus_text = "、".join(focus_points) if focus_points else "N/A"
    return f"""你是技术面试项目讲解教练，擅长基于历史证据帮助候选人组织项目讲解稿。

请为候选人生成一份适合面试口述的项目讲解稿。

强约束：
- 只能基于【历史证据】描述已经发生的项目事实或候选人历史表现。
- 涉及项目事实、历史实现、历史表现的判断，必须引用证据编号，例如 [E1]。
- 如果证据不足，必须明确写“证据不足，建议补充”，不能编造未在证据中出现的实现。
- 可以给表达建议和补充建议，但不能把建议包装成已经完成的事实。
- 不要声称已经实现真实 embedding API、rerank、生产级权限系统等证据中没有出现的能力。
- 如果【历史证据】为“无可用历史证据。”，只能给通用讲解框架，不要生成具体历史实现判断，也不要引用不存在的 [E1]。

【项目名称】
{project_name}

【目标岗位】
{target_role}

【口述时长】
{duration_minutes} 分钟

【语言】
{language}

【风格】
{style}

【重点方向】
{focus_text}

【历史证据】
{evidence_context}

请输出 Markdown，结构固定如下：

# 1. 开场一句话

# 2. 项目背景和问题

# 3. 技术架构

# 4. 我的核心贡献

# 5. 难点与解决方案

# 6. 工程化亮点

# 7. RAG / Agent / 后端能力亮点

# 8. 面试官可能追问

# 9. 过度包装风险提醒

要求：
- 内容要能直接用于面试口述。
- 事实性描述尽量引用 [E1] / [E2]。
- 证据不足处要直接标注“证据不足，建议补充”。
- 不要输出 JSON。
"""


class ProjectPitchSkill(BaseSkill):
    """Generate an evidence-based project pitch for interviews."""

    @property
    def spec(self) -> SkillSpec:
        """Return skill metadata."""
        return SkillSpec(
            name=SKILL_NAME,
            description="Generate an evidence-based project pitch for interviews.",
            input_schema={
                "project_name": "str, required",
                "target_role": "str, required",
                "query": "str, optional, default project_name",
                "duration_minutes": "int, optional, default 3",
                "language": "str, optional, default zh",
                "retriever_type": "keyword | fts | embedding | hybrid, default keyword",
                "top_k": "int, optional, default 5",
                "include_prompt": "bool, optional, default false",
                "focus_points": "list[str], optional",
                "style": "str, optional, default interview",
            },
            output_schema={
                "pitch": "str",
                "raw_output": "str",
                "evidence_context": "str",
                "used_evidence_count": "int",
                "evidence_validation": "dict",
                "prompt": "str | None",
                "sections": "list[str]",
            },
            supported_retriever_types=("keyword", "fts", "embedding", "hybrid"),
            requires_evidence=True,
            supports_async=True,
            tags=("interview", "project", "pitch", "rag"),
        )

    def run(self, request: SkillRequest) -> SkillResult:
        """Run project pitch generation using existing retrieval and LLM services."""
        if request.skill_name != self.name:
            raise ValueError(f"SkillRequest skill_name must be {self.name}")

        inputs = request.inputs
        context = request.context

        project_name = str(inputs.get("project_name", "")).strip()
        if not project_name:
            raise ValueError("project_name is required")

        target_role = str(inputs.get("target_role", "")).strip()
        if not target_role:
            raise ValueError("target_role is required")

        db_path = str(context.get("db_path", "")).strip()
        if not db_path:
            raise ValueError("context.db_path is required")

        retriever_type = str(inputs.get("retriever_type", "keyword")).strip() or "keyword"
        query = str(inputs.get("query", "")).strip() or project_name
        top_k = int(inputs.get("top_k", 5))
        duration_minutes = int(inputs.get("duration_minutes", 3))
        language = str(inputs.get("language", "zh")).strip() or "zh"
        style = str(inputs.get("style", "interview")).strip() or "interview"
        include_prompt = _as_bool(inputs.get("include_prompt", False))
        focus_points = _as_str_list(inputs.get("focus_points"))

        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")

        retriever = get_retriever(retriever_type)
        results = retriever.retrieve(
            db_path=db_path,
            query=query,
            top_k=top_k,
        )
        evidence_context = build_evidence_context(results, max_chunks=top_k)
        prompt = build_project_pitch_prompt(
            project_name=project_name,
            target_role=target_role,
            duration_minutes=duration_minutes,
            language=language,
            focus_points=focus_points,
            style=style,
            evidence_context=evidence_context,
        )
        raw_output = generate_text(prompt)

        valid_refs = extract_valid_evidence_ids(evidence_context)
        used_refs = extract_evidence_refs_from_text(raw_output)
        issues = validate_evidence_refs(used_refs, valid_refs)
        evidence_validation = evidence_validation_result_to_dict(
            EvidenceValidationResult(
                is_valid=not issues,
                valid_evidence_ids=valid_refs,
                used_evidence_refs=used_refs,
                issues=issues,
            )
        )

        output: dict[str, Any] = {
            "pitch": raw_output,
            "raw_output": raw_output,
            "evidence_context": evidence_context,
            "used_evidence_count": len(results),
            "evidence_validation": evidence_validation,
            "prompt": prompt if include_prompt else None,
            "sections": _extract_markdown_sections(raw_output),
        }
        metadata: dict[str, Any] = {
            "source": "project_pitch_skill",
            "project_name": project_name,
            "target_role": target_role,
            "retriever_type": retriever_type,
            "top_k": top_k,
            "duration_minutes": duration_minutes,
            "language": language,
            "used_evidence_count": len(results),
            "evidence_validation": evidence_validation,
        }

        return SkillResult(
            skill_name=self.name,
            output=output,
            metadata=metadata,
        )
