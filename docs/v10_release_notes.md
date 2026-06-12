# InterviewAce V10 Release Notes

## 1. Positioning

InterviewAce V10 positions the project as a **Skill-based Interview Agent Backend**.

The V10 line connects the earlier RAG and evidence-grounding work with a reusable Skill Layer:

```text
RAG + Evidence Validation + Skill Layer + Skill API + Skill Evaluation + Rule-based Router
```

The goal is not to add another one-off endpoint. The goal is to make interview coaching capabilities discoverable, reusable, testable, and callable through a consistent contract.

## 2. V10 Milestones

### V10.1 Skill Spec / Registry

V10.1 introduced the base abstractions:

- `SkillRequest`
- `SkillResult`
- `SkillSpec`
- `BaseSkill`
- `SkillRegistry`

This created a stable contract for future business skills without coupling them directly to FastAPI, Celery, or UI code.

### V10.2 InterviewPreparationSkill

V10.2 added the first business skill:

- `interview_preparation`

It wraps the existing structured preparation service and returns a `SkillResult`.

Key points:

- reuses structured preparation service;
- supports `retriever_type`;
- preserves evidence validation metadata;
- does not duplicate RAG, prompt, parser, or LLM logic.

### V10.3 Skill API / Async Task

V10.3 exposed the Skill Layer through the existing API and Celery infrastructure:

- `GET /api/skills`
- `GET /api/skills/{skill_name}`
- `POST /api/skills/{skill_name}/run`
- `POST /api/skills/{skill_name}/tasks`

Async skill tasks reuse:

- Celery task `skills.run_skill`;
- SQLite `task_records`;
- existing `GET /api/tasks/{task_id}` task status query.

### V10.4 ProjectPitchSkill

V10.4 added the second business skill:

- `project_pitch`

It generates an evidence-based project pitch for interviews.

Key points:

- uses `get_retriever(retriever_type)`;
- builds Evidence Context;
- generates a project pitch with evidence citation requirements;
- validates evidence references in the generated text;
- is callable through the generic Skill API, both sync and async.

### V10.5 Skill Evaluation

V10.5 added lightweight deterministic Skill Evaluation:

- `SkillEvalCase`
- `SkillEvalMetric`
- `SkillEvalResult`
- `evaluate_skill_result`
- `run_skill_eval_case`
- `run_skill_eval_cases`

It checks result structure, required output keys, required metadata keys, success state, error messages, and evidence validation status.

This is not LLM-as-judge. It does not call models or external services.

### V10.6 Rule-based Skill Router

V10.6 added a deterministic router:

- explicit `skill_name` priority;
- keyword matching;
- tag matching;
- skill name matching;
- description token matching;
- candidate score and reason output.

The router only recommends a skill. It does not execute `skill.run()` and does not implement an Agent Loop.

## 3. Default Skills

The default skill registry currently includes:

- `interview_preparation`
- `project_pitch`

## 4. Current Non-goals

V10 intentionally does not implement:

- `skill_runs` table;
- LLM-based router;
- complex Agent Loop;
- frontend UI for skills;
- online deployment;
- additional business skills beyond the current two;
- real embedding API integration;
- reranker.

## 5. Test Status

Historical V10 test checkpoints:

- V10.4 full suite: `386 passed, 2 skipped`
- V10.5 full suite: `399 passed, 2 skipped`
- V10.6 full suite: `411 passed, 2 skipped`
- V10.7 final suite: `411 passed, 2 skipped`

## 6. Next Recommendations

Before adding more features, spend time consolidating the concepts already implemented:

- RAG retrieval paths;
- Evidence Context and citation rules;
- evidence validation;
- Skill Spec / Registry;
- sync and async Skill API;
- task_records;
- Skill Evaluation;
- Rule-based Router.

For interview preparation, the next practical step is to strengthen:

- project pitch wording;
- backend engineering talking points;
- RAG / Agent tradeoff explanations;
- Redis / Celery / task consistency explanations;
- industry and role-specific interview knowledge.

Future engineering directions:

- persistent `skill_runs`;
- Router API;
- LLM-based router;
- Agent Loop;
- skill UI integration;
- real embedding provider;
- reranker;
- richer RAG Eval / claim verification.
