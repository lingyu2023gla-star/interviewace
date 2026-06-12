# Skill Evaluation

V10.5 adds a lightweight, deterministic Skill Evaluation layer for checking whether a `SkillResult` satisfies basic quality requirements.

This is not an LLM judge. It does not call models, retrievers, Redis, Celery, or databases by itself.

## 1. Purpose

Skill Evaluation helps keep business skills testable as the Skill Layer grows.

It answers questions such as:

- Did the skill run successfully?
- Does the output contain required keys?
- Does metadata contain required keys?
- Does the result include `evidence_validation`?
- Is `evidence_validation.is_valid` true when required?
- Did the skill return an unexpected `error_message`?

This is useful for regression tests and future golden-case evaluation.

## 2. Data Structures

### SkillEvalCase

`SkillEvalCase` defines what to run and what to check.

| Field | Description |
| --- | --- |
| `name` | Stable eval case name |
| `skill_name` | Target skill name |
| `request` | `SkillRequest` passed to the skill |
| `required_output_keys` | Output keys that must exist |
| `required_metadata_keys` | Metadata keys that must exist |
| `require_success` | Whether `SkillResult.success` must be true |
| `require_evidence_validation` | Whether evidence validation metadata must exist |
| `require_valid_evidence` | Whether `evidence_validation.is_valid` must be true |

### SkillEvalMetric

`SkillEvalMetric` represents one check.

| Field | Description |
| --- | --- |
| `name` | Metric name |
| `passed` | Whether the metric passed |
| `message` | Human-readable result |
| `details` | Extra machine-readable details |

### SkillEvalResult

`SkillEvalResult` is the final result for one case.

| Field | Description |
| --- | --- |
| `case_name` | Eval case name |
| `skill_name` | Target skill name |
| `passed` | Whether all metrics passed |
| `metrics` | List of metric results |
| `result` | Original `SkillResult`, if execution succeeded |
| `error_message` | Captured exception message, if execution failed |

## 3. evaluate_skill_result

`evaluate_skill_result(case, result)` checks:

- `result.skill_name == case.skill_name`
- `result.success is True` when `require_success=True`
- `result.error_message is None` when `require_success=True`
- all `required_output_keys` exist in `result.output`
- all `required_metadata_keys` exist in `result.metadata`
- `evidence_validation` exists when required
- `evidence_validation.is_valid is True` when required

`evidence_validation` can be found in either:

- `result.metadata["evidence_validation"]`
- `result.output["evidence_validation"]`

## 4. run_skill_eval_case

`run_skill_eval_case(registry, case)`:

```text
registry.get(case.skill_name)
  -> skill.run(case.request)
  -> evaluate_skill_result(case, result)
```

If the skill raises an exception, the eval result is returned with:

- `passed=False`
- `result=None`
- `error_message=str(exc)`

The exception is not propagated to the caller.

## 5. run_skill_eval_cases

`run_skill_eval_cases(registry, cases)` runs cases one by one and preserves input order.

One failed case does not stop the remaining cases.

## 6. Boundaries

Current V10.5 does not implement:

- LLM-as-judge
- semantic scoring
- complex claim verifier
- unsupported claim rate
- database persistence
- API endpoint
- Celery task
- `skill_runs` table

## 7. Roadmap

Possible next steps:

- RAG Eval for evidence-grounded outputs
- Claim Verifier for unsupported project claims
- Golden cases for each Skill
- Aggregate metrics such as missing field rate and invalid evidence rate
- Persistent `skill_runs` and eval reports
