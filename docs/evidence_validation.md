# Evidence Ref Validation

V9.6 adds a lightweight evidence reference validator for structured preparation plans.

## 1. Purpose

Prompt rules alone cannot guarantee that an LLM only cites available evidence. The validator adds a deterministic check after structured JSON parsing:

```text
evidence_context
  -> valid evidence ids: E1 / E2 / E3

structured plan output
  -> used evidence refs
  -> validation issues
  -> metadata.evidence_validation
```

The validator does not call another LLM and does not verify semantic claim truth. It only checks whether evidence references are present, valid, and used where historical judgments require them.

## 2. What It Checks

The validator checks:

- valid evidence ids extracted from Evidence Context, such as `[E1]`;
- used evidence refs in structured output, such as `[E1]` or `E1`;
- unknown refs, such as `E9` when only `E1` exists;
- missing evidence refs for concrete `evidence_based_judgments`;
- concrete historical judgments when evidence context is empty.

Issue codes:

| Code | Meaning |
| --- | --- |
| `unknown_evidence_ref` | The output referenced an evidence id not present in context. |
| `missing_required_evidence_ref` | A concrete historical judgment did not cite evidence. |
| `empty_evidence_context_with_judgment` | The output made a concrete historical judgment while no evidence exists. |

## 3. Evidence ID Extraction

Valid evidence ids are parsed from the existing Evidence Context format:

```text
[E1]
来源类型：turn_feedback
证据内容：
...
```

The parser extracts `E1`, `E2`, `E3`, etc. It does not change Evidence Context formatting.

## 4. Output Ref Extraction

Used refs are extracted from:

- explicit `evidence_refs` fields in structured JSON;
- text fields containing `[E1]`;
- standalone `E1` tokens.

The extraction avoids matching refs embedded inside ordinary words or email-like strings.

## 5. Structured Plan Integration

`preparation/structured_service.py` runs validation after:

```text
generate_text(prompt)
  -> parse_structured_preparation_plan(raw_output)
  -> validate_structured_plan_evidence_refs(...)
```

The validation result is stored in:

```text
structured_plan.metadata["evidence_validation"]
```

Example:

```json
{
  "is_valid": false,
  "valid_evidence_ids": ["E1"],
  "used_evidence_refs": ["E9"],
  "issues": [
    {
      "code": "unknown_evidence_ref",
      "message": "Evidence reference E9 is not present in evidence_context.",
      "field_path": null,
      "evidence_ref": "E9"
    }
  ]
}
```

## 6. Non-blocking By Default

Validation is non-blocking by default. If issues exist, the structured result is still returned with `metadata.evidence_validation.is_valid = false`.

This keeps old API behavior compatible while making hallucination risk visible to callers.

## 7. Current Scope

V9.6 intentionally does not implement:

- complex claim verification;
- LLM-based judge / verifier;
- reranking;
- automatic repair or retry;
- changes to retriever defaults;
- changes to Evidence Context format.

## 8. Tests

```bash
.venv/bin/python -m pytest tests/test_evidence_validator.py -v
.venv/bin/python -m pytest tests/test_structured_preparation_service.py -v
```

Default tests do not require network, Redis, Docker, Celery worker, real LLM calls, or real embedding APIs.

## 9. Next Steps

Future versions can add:

- strict mode at API/task boundary;
- claim-level verifier;
- RAG evaluation reports;
- automatic retry with a stricter prompt when validation fails.
