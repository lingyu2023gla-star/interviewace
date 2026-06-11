"""Parse and validate structured preparation plan LLM output."""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from preparation.structured_schemas import StructuredPreparationPlan


class StructuredOutputParseError(ValueError):
    """Raised when structured LLM output cannot be parsed or validated."""


_JSON_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_json_object(text: str) -> str:
    """Extract a JSON object from plain text or a markdown JSON fence."""
    if not text or not text.strip():
        raise StructuredOutputParseError("Structured output is empty.")

    match = _JSON_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise StructuredOutputParseError("No JSON object found in structured output.")

    return text[start : end + 1].strip()


def parse_structured_preparation_plan(text: str) -> StructuredPreparationPlan:
    """Parse LLM text into a validated StructuredPreparationPlan."""
    json_text = extract_json_object(text)
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise StructuredOutputParseError(f"Invalid JSON output: {exc.msg}") from exc

    try:
        return StructuredPreparationPlan(**data)
    except ValidationError as exc:
        message = str(exc).replace("\n", " ")
        if len(message) > 500:
            message = message[:500] + "..."
        raise StructuredOutputParseError(
            f"Structured preparation plan validation failed: {message}"
        ) from exc


def structured_plan_to_dict(plan: StructuredPreparationPlan) -> dict:
    """Convert a structured plan to a dict across Pydantic v1/v2."""
    if hasattr(plan, "model_dump"):
        return plan.model_dump()
    return plan.dict()
