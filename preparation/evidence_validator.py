"""Validate evidence references in structured preparation plan output."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import re


@dataclass(frozen=True)
class EvidenceValidationIssue:
    """One evidence citation validation issue."""

    code: str
    message: str
    field_path: str | None = None
    evidence_ref: str | None = None


@dataclass(frozen=True)
class EvidenceValidationResult:
    """Evidence citation validation summary."""

    is_valid: bool
    valid_evidence_ids: set[str]
    used_evidence_refs: set[str]
    issues: list[EvidenceValidationIssue]


_BRACKET_REF_RE = re.compile(r"\[\s*(E\d+)\s*\]", re.IGNORECASE)
_TOKEN_REF_RE = re.compile(r"(?<![A-Za-z0-9_])E\d+(?![A-Za-z0-9_])", re.IGNORECASE)


def normalize_evidence_ref(ref: str) -> str:
    """Normalize evidence references such as '[e1]' and 'E1' to 'E1'."""
    cleaned = (ref or "").strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1].strip()
    return cleaned.upper()


def extract_valid_evidence_ids(evidence_context: str | None) -> set[str]:
    """Extract valid evidence ids from an evidence context string."""
    if not evidence_context:
        return set()
    return {normalize_evidence_ref(match) for match in _BRACKET_REF_RE.findall(evidence_context)}


def extract_evidence_refs_from_text(text: str | None) -> set[str]:
    """Extract evidence references from arbitrary model output text."""
    if not text:
        return set()

    refs = {normalize_evidence_ref(match) for match in _BRACKET_REF_RE.findall(text)}
    refs.update(normalize_evidence_ref(match.group(0)) for match in _TOKEN_REF_RE.finditer(text))
    return refs


def validate_evidence_refs(
    used_refs: set[str],
    valid_refs: set[str],
    field_path: str | None = None,
) -> list[EvidenceValidationIssue]:
    """Return issues for evidence refs that are not available in context."""
    issues: list[EvidenceValidationIssue] = []
    normalized_valid = {normalize_evidence_ref(ref) for ref in valid_refs}
    for ref in sorted(normalize_evidence_ref(ref) for ref in used_refs):
        if ref not in normalized_valid:
            issues.append(
                EvidenceValidationIssue(
                    code="unknown_evidence_ref",
                    message=f"Evidence reference {ref} is not present in evidence_context.",
                    field_path=field_path,
                    evidence_ref=ref,
                )
            )
    return issues


def evidence_validation_result_to_dict(result: EvidenceValidationResult) -> dict[str, Any]:
    """Convert validation result to JSON-serializable dict."""
    return {
        "is_valid": result.is_valid,
        "valid_evidence_ids": sorted(result.valid_evidence_ids),
        "used_evidence_refs": sorted(result.used_evidence_refs),
        "issues": [asdict(issue) for issue in result.issues],
    }


def _to_plain_data(value: Any) -> Any:
    """Convert Pydantic/dataclass values to plain Python containers."""
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return value


def _collect_refs_from_value(value: Any, field_path: str, issues: list[EvidenceValidationIssue]) -> set[str]:
    """Collect evidence refs recursively from evidence_refs fields and strings."""
    value = _to_plain_data(value)
    refs: set[str] = set()

    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{field_path}.{key}" if field_path else str(key)
            if key == "evidence_refs":
                item_refs = set()
                if isinstance(item, list):
                    item_refs = {normalize_evidence_ref(str(ref)) for ref in item if str(ref).strip()}
                elif item:
                    item_refs = {normalize_evidence_ref(str(item))}
                refs.update(item_refs)
            else:
                refs.update(_collect_refs_from_value(item, child_path, issues))
        return refs

    if isinstance(value, list):
        for index, item in enumerate(value):
            child_path = f"{field_path}[{index}]"
            refs.update(_collect_refs_from_value(item, child_path, issues))
        return refs

    if isinstance(value, str):
        refs.update(extract_evidence_refs_from_text(value))

    return refs


def _is_concrete_judgment(judgment: Any) -> bool:
    """Return whether a judgment appears to claim historical performance."""
    data = _to_plain_data(judgment)
    if not isinstance(data, dict):
        return False

    judgment_type = str(data.get("type", "")).strip().lower()
    content = str(data.get("content", ""))
    if judgment_type == "insufficient_evidence":
        return False
    if "历史证据不足" in content or "证据不足" in content:
        return False
    return bool(content.strip())


def validate_structured_plan_evidence_refs(
    structured_plan: Any,
    evidence_context: str | None,
) -> EvidenceValidationResult:
    """Validate structured preparation plan evidence references."""
    valid_refs = extract_valid_evidence_ids(evidence_context)
    data = _to_plain_data(structured_plan)
    if not isinstance(data, dict):
        data = {}

    issues: list[EvidenceValidationIssue] = []
    used_refs = _collect_refs_from_value(data, "", issues)
    issues.extend(validate_evidence_refs(used_refs, valid_refs))

    judgments = data.get("evidence_based_judgments") or []
    if isinstance(judgments, list):
        for index, judgment in enumerate(judgments):
            field_path = f"evidence_based_judgments[{index}]"
            if not _is_concrete_judgment(judgment):
                continue

            judgment_refs = _collect_refs_from_value(judgment, field_path, issues)
            if not valid_refs:
                issues.append(
                    EvidenceValidationIssue(
                        code="empty_evidence_context_with_judgment",
                        message="Concrete historical judgment appears while evidence_context is empty.",
                        field_path=field_path,
                    )
                )
            if not judgment_refs:
                issues.append(
                    EvidenceValidationIssue(
                        code="missing_required_evidence_ref",
                        message="Concrete historical judgment must cite at least one evidence id.",
                        field_path=field_path,
                    )
                )

    return EvidenceValidationResult(
        is_valid=not issues,
        valid_evidence_ids=valid_refs,
        used_evidence_refs=used_refs,
        issues=issues,
    )
