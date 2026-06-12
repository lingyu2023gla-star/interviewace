# ProjectPitchSkill

`ProjectPitchSkill` 是 V10.4 新增的业务 Skill，用于基于 InterviewAce 已沉淀的 `knowledge_chunks` 和 Evidence Context 生成面试项目讲解稿。

它不是新的 API endpoint，也不是新的 Celery task。它复用 V10.3 的通用 Skill API：

- `POST /api/skills/project_pitch/run`
- `POST /api/skills/project_pitch/tasks`

异步任务仍然通过 `GET /api/tasks/{task_id}` 查询。

## 1. Purpose

这个 Skill 面向面试表达场景，帮助候选人把 InterviewAce 或其他项目讲成一段有证据支撑的项目介绍。

输出重点包括：

- 项目是什么
- 解决什么问题
- 技术架构
- 我的核心贡献
- 难点与解决方案
- 工程化亮点
- RAG / Agent / 后端能力亮点
- 面试官可能追问
- 过度包装风险提醒

## 2. Input

`SkillRequest.inputs` 支持：

| Field | Required | Description |
| --- | --- | --- |
| `project_name` | yes | 项目名称，例如 `InterviewAce` |
| `target_role` | yes | 目标岗位，例如 `Agent / RAG 应用工程师` |
| `query` | no | 检索 query，默认使用 `project_name` |
| `duration_minutes` | no | 口述时长，默认 3 |
| `language` | no | 输出语言，默认 `zh` |
| `retriever_type` | no | `keyword` / `fts` / `embedding` / `hybrid`，默认 `keyword` |
| `top_k` | no | 检索证据数量，默认 5 |
| `include_prompt` | no | 是否返回 prompt，默认 false |
| `focus_points` | no | 重点方向，例如 `["RAG", "FastAPI", "Celery"]` |
| `style` | no | 输出风格，默认 `interview` |

`SkillRequest.context` 需要：

| Field | Required | Description |
| --- | --- | --- |
| `db_path` | yes | SQLite 数据库路径 |

API 层会默认把 `INTERVIEWACE_DB_PATH` 注入到 context。

## 3. Output

`SkillResult.output` 包含：

| Field | Description |
| --- | --- |
| `pitch` | 模型生成的项目讲解稿 |
| `raw_output` | 原始模型输出 |
| `evidence_context` | `[E1]` / `[E2]` 格式证据上下文 |
| `used_evidence_count` | 使用的证据数量 |
| `evidence_validation` | evidence refs 校验结果 |
| `prompt` | `include_prompt=true` 时返回 |
| `sections` | 从 Markdown heading 提取的章节名 |

`SkillResult.metadata` 包含：

- `source="project_pitch_skill"`
- `project_name`
- `target_role`
- `retriever_type`
- `top_k`
- `duration_minutes`
- `language`
- `used_evidence_count`
- `evidence_validation`

## 4. Retrieval

ProjectPitchSkill 不直接查询数据库，也不直接调用 `search_knowledge_chunks`。

它通过：

```text
get_retriever(retriever_type)
  -> retriever.retrieve(...)
  -> build_evidence_context(...)
```

支持：

- `keyword`
- `fts`
- `embedding`
- `hybrid`

当前默认仍然是 `keyword`。选择 `embedding` / `hybrid` 时，需要本地 SQLite `chunk_embeddings` 中已有对应 embedding；当前不会自动调用真实 embedding API。

## 5. Anti-Hallucination

ProjectPitchSkill 使用两层防幻觉约束：

1. Prompt 要求所有项目事实和历史表现判断必须引用 `[E1]` / `[E2]`。
2. 生成后用 evidence ref validator 检查输出中引用的证据编号是否存在于 Evidence Context。

如果模型输出了不存在的 `[E9]`，结果不会默认中断，但 `evidence_validation.is_valid=false`，并记录 `unknown_evidence_ref` issue。

## 6. Sync API Example

```bash
curl -s -X POST http://127.0.0.1:8000/api/skills/project_pitch/run \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "project_name": "InterviewAce",
      "target_role": "Agent / RAG 应用工程师",
      "query": "InterviewAce RAG FastAPI Celery",
      "retriever_type": "keyword",
      "duration_minutes": 3,
      "focus_points": ["RAG", "FastAPI", "Celery"]
    }
  }' | python -m json.tool
```

## 7. Async API Example

```bash
curl -s -X POST http://127.0.0.1:8000/api/skills/project_pitch/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "project_name": "InterviewAce",
      "target_role": "Agent / RAG 应用工程师",
      "retriever_type": "keyword"
    }
  }' | python -m json.tool
```

然后使用返回的 `task_id`：

```bash
curl -s http://127.0.0.1:8000/api/tasks/<task_id> | python -m json.tool
```

## 8. Boundaries

当前不做：

- 不新增 API route
- 不新增 Celery task
- 不新增 `skill_runs` 表
- 不实现 Skill Router
- 不调用真实 embedding API
- 不改变 InterviewPreparationSkill 行为
- 不改变 preparation 主链路

测试中通过 monkeypatch mock LLM，不依赖真实 Redis、Docker、Celery worker、网络或 embedding API。
