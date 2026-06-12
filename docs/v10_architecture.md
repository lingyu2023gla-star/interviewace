# InterviewAce V10 Architecture

## 1. Overview

InterviewAce V10 organizes the system around reusable Skills while preserving the existing RAG, Evidence Context, FastAPI, Celery, and task_records infrastructure.

The key architecture goal is:

```text
make interview coaching capabilities discoverable, callable, testable, and evidence-grounded
```

## 2. Architecture Diagram

```text
User / Client
  ↓
FastAPI Skill API
  ↓
Skill Registry
  ↓
InterviewPreparationSkill / ProjectPitchSkill
  ↓
Retriever Layer
  ├─ KeywordRetriever
  ├─ EmbeddingRetriever
  └─ HybridRetriever
  ↓
Evidence Context
  ↓
LLM Generation
  ↓
Evidence Ref Validator
  ↓
SkillResult
  ↓
Skill Evaluation / task_records
```

## 3. Layer Responsibilities

### API Layer

The FastAPI layer exposes generic Skill endpoints:

- `GET /api/skills`
- `GET /api/skills/{skill_name}`
- `POST /api/skills/{skill_name}/run`
- `POST /api/skills/{skill_name}/tasks`

The API layer only handles request validation, registry lookup, task submission, and response conversion. It does not write SQL, build prompts, or directly initialize LLM clients.

### Skill Registry

`SkillRegistry` manages available skills.

The default registry currently contains:

- `interview_preparation`
- `project_pitch`

It is created through `create_default_skill_registry()` and is not a global mutable singleton.

### Skill Layer

Skills provide a stable business interface:

```text
SkillRequest -> Skill.run(...) -> SkillResult
```

Current skills:

- `InterviewPreparationSkill`: wraps structured preparation plan generation.
- `ProjectPitchSkill`: generates an evidence-based project pitch.

Skills are adapters. They reuse lower-level services instead of duplicating retrieval, prompt, parser, LLM, or evidence validation logic.

### Retriever Layer

The retriever layer hides the retrieval implementation behind a shared interface.

Supported `retriever_type` values:

- `keyword`
- `fts`
- `embedding`
- `hybrid`

Default behavior remains `keyword`. `embedding` and `hybrid` are opt-in and require existing SQLite `chunk_embeddings` rows. The system does not call a real embedding API automatically.

### Evidence Context

Search results are converted into citation-ready evidence blocks:

```text
[E1]
来源类型：turn_feedback
来源ID：turn:1:feedback
主题：Agent 架构
证据内容：
...
```

Evidence Context is the bridge between retrieval and generation. It makes later claims traceable.

### LLM Generation

LLM calls remain centralized through the existing text generation wrapper.

The Skill layer does not create new LLM clients. Tests monkeypatch LLM calls and do not call real APIs.

### Evidence Ref Validator

The validator checks whether generated output references valid evidence IDs.

It can detect:

- unknown evidence refs, such as `E9` when only `E1` exists;
- missing required evidence refs in structured preparation judgments;
- concrete historical judgments when Evidence Context is empty.

It is deterministic and does not call another LLM.

### Skill Evaluation

Skill Evaluation checks `SkillResult` quality:

- success flag;
- error message;
- required output keys;
- required metadata keys;
- evidence_validation existence;
- evidence_validation validity.

It is a lightweight regression guard, not a semantic judge.

### task_records

Async Skill calls reuse Celery and `task_records`.

```text
POST /api/skills/{skill_name}/tasks
  -> create task_records PENDING
  -> Celery skills.run_skill
  -> update STARTED / SUCCESS / FAILURE
  -> GET /api/tasks/{task_id}
```

Redis remains the broker and short-term result backend. SQLite `task_records` provides longer-lived local auditability.

## 4. Why No Complex Agent Loop Yet

V10 intentionally avoids a complex Agent Loop.

Reasons:

- Skills must first be stable, registerable, callable, and testable.
- The Rule-based Router currently recommends a Skill but does not execute it.
- Avoiding automatic multi-step loops keeps side effects explicit.
- Existing sync and async APIs are easier to test and debug.
- Evidence validation and Skill Evaluation should mature before autonomous retries or multi-step planning.

## 5. Architecture Highlights

- Skill and API are decoupled.
- Skill and concrete retriever implementations are decoupled.
- Sync and async execution reuse the same Skill layer.
- Evidence Context and Evidence Ref Validator reduce hallucination risk.
- Skill Evaluation makes output quality testable.
- `task_records` makes async task status and results inspectable beyond Redis result expiration.

## 6. Current Boundaries

V10 does not add:

- new database tables beyond existing `task_records`;
- `skill_runs`;
- LLM-based router;
- Agent Loop;
- frontend skill UI;
- real embedding API;
- reranker.

These are future roadmap items, not current implementation.
