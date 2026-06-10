# InterviewAce

InterviewAce 是一个 AI 面试复盘与准备系统，支持从面试转写文本中进行结构化复盘、能力诊断、知识库沉淀、证据检索、基于历史证据的准备计划生成，并通过 FastAPI + Celery/Redis 提供服务化能力。

## 1. 项目背景

面试复盘通常依赖人工回忆，容易遗漏关键问题：哪些回答没有说清楚、哪些技术点只是提到但没有展开、哪些能力本场没有被验证，都很难在面试后准确还原。

大模型可以帮助整理面试对话、诊断回答问题并生成改进建议，但直接把完整面试丢给 LLM 总结，容易出现幻觉或过度推断。InterviewAce 因此引入了 `knowledge_chunks`、Evidence Context 和引用式 Prompt：先把复盘结果沉淀为可追溯的知识片段，再通过检索和证据编号约束后续建议。

项目从 Streamlit MVP 演进为一个后端大模型应用：保留本地可用的复盘驾驶舱，同时提供 FastAPI、知识库检索和 Celery 异步任务能力。

## 2. 核心功能

- 面试转写文本解析，支持讯飞听见导出的 `.txt` 文本。
- full-context 面试分析，基于完整上下文进行结构化复盘。
- 多维能力诊断，覆盖技术概念、技术深度、后端工程、Agent、RAG、Prompt Engineering 等维度。
- STAR / 技术表达复盘，帮助定位回答结构、项目证据和交付感问题。
- 历史面试记录保存，沉淀 sessions / turns / questions。
- 面试知识库 `knowledge_chunks`，支持可追溯、幂等写入。
- keyword / SQLite FTS 检索，并在 FTS 不可用时降级到 LIKE 检索。
- Evidence Context 构建，使用 `[E1]` / `[E2]` 证据编号约束后续判断。
- 基于历史证据生成面试准备计划。
- FastAPI 接口服务，暴露检索、证据上下文和准备计划能力。
- Redis / Celery 异步任务接口，支持任务提交、状态查询和本地 ping 验收。
- 本地可选 Redis + Celery worker 集成验收。

当前没有实现 embedding 向量库、rerank 或模型微调；知识库检索以 keyword / FTS 为主。

## 3. 技术栈

- Python 3.11+
- Streamlit
- FastAPI
- Pydantic
- SQLite
- SQLite FTS / keyword search
- Redis
- Celery
- pytest
- Jinja2
- Plotly
- DeepSeek / OpenAI-compatible API

依赖版本以 [requirements.txt](requirements.txt) 为准。

## 4. 系统架构

```text
Streamlit UI
    ↓
core / agent
    ↓
knowledge
    ↓
preparation
    ↓
FastAPI api
    ↓
Celery worker
    ↓
Redis broker / result backend
```

```text
app.py / pages/       Streamlit UI
core/                 转写解析、LLM 分析、基础存储
agent/                Agent Orchestrator 与 Tool 链路
prompts/              Prompt 模板与 Prompt Builder
knowledge/            knowledge_chunks、检索、Evidence Context
preparation/          准备计划生成 service
api/                  FastAPI router 和 schema
worker/               Celery app 和异步任务
tests/                单元测试、API 测试、可选集成测试
scripts/              本地启动脚本
docs/                 补充文档
```

## 5. 已完成版本

| 阶段 | 能力 | 说明 |
|---|---|---|
| V1 | Knowledge Base Model | 新增 `knowledge_chunks` 数据模型、索引和幂等写入服务。 |
| V2 | Keyword / FTS Search | 基于 SQLite FTS5 / LIKE fallback 实现关键词检索。 |
| V3 | Evidence Context | 将检索结果格式化为 `[E1]` / `[E2]` 引用式证据上下文。 |
| V4.1 | Preparation Prompt Builder | 构建基于历史证据的面试准备计划 Prompt。 |
| V4.2 | Preparation Service | 串联 search -> evidence -> prompt -> LLM，生成准备计划。 |
| V5 | FastAPI API | 暴露 search / evidence-context / preparation plan API。 |
| V6.1 | Celery Task API | 新增异步任务提交和任务状态查询接口。 |
| V6.2 | Redis / Celery Integration | 新增 ping task、本地 worker 验收脚本和可选 integration test。 |

## 6. 快速开始

### 1. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. 安装依赖

```bash
.venv/bin/pip install -r requirements.txt
```

### 3. 配置环境变量

LLM 调用使用项目现有的 DeepSeek / OpenAI-compatible 配置，关键变量见 [core/analyzer.py](core/analyzer.py)。本地通常需要配置：

```bash
DEEPSEEK_API_KEY=...
```

### 4. 运行测试

```bash
.venv/bin/python -m pytest tests/ -v
```

默认测试不依赖 Redis / Celery worker，也不会调用真实 LLM。

## 7. Streamlit 运行方式

```bash
streamlit run app.py
```

启动后访问：

```text
http://localhost:8501
```

Streamlit 入口适合本地上传面试转写、查看复盘、题库和成长趋势。

## 8. FastAPI 运行方式

推荐使用脚本：

```bash
./scripts/run_api.sh
```

也可以直接启动：

```bash
uvicorn api.main:app --reload
```

访问 API 文档：

```text
http://127.0.0.1:8000/docs
```

## 9. API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| POST | `/api/knowledge/search` | 知识库检索 |
| POST | `/api/knowledge/evidence-context` | 构建 Evidence Context |
| POST | `/api/preparation/plan` | 同步生成准备计划 |
| POST | `/api/preparation/plan-tasks` | 异步提交准备计划任务 |
| POST | `/api/tasks/ping` | 提交 Celery ping task |
| GET | `/api/tasks/{task_id}` | 查询任务状态 |

## 10. API 示例

### Knowledge Search

```bash
curl -s -X POST http://127.0.0.1:8000/api/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Agent RAG",
    "top_k": 5
  }' | python -m json.tool
```

### Evidence Context

```bash
curl -s -X POST http://127.0.0.1:8000/api/knowledge/evidence-context \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Agent RAG",
    "top_k": 5
  }' | python -m json.tool
```

### Async Ping Task

```bash
curl -s -X POST http://127.0.0.1:8000/api/tasks/ping | python -m json.tool
```

查询任务：

```bash
curl -s http://127.0.0.1:8000/api/tasks/<task_id> | python -m json.tool
```

实际使用时不要带尖括号，替换为真实 `task_id`。

## 11. Redis / Celery 本地集成

### 1. 启动 Redis

Docker：

```bash
./scripts/run_redis_docker.sh
```

如果本机没有 Docker，可以使用本地 Redis：

```bash
brew install redis
./scripts/run_redis_local.sh
redis-cli ping
```

也可以直接运行：

```bash
redis-server
redis-cli ping
```

### 2. 启动 Celery worker

```bash
./scripts/run_worker.sh
```

### 3. 启动 API

```bash
./scripts/run_api.sh
```

### 4. 验证 ping task

```bash
curl -s -X POST http://127.0.0.1:8000/api/tasks/ping | python -m json.tool
```

然后用返回的 `task_id` 查询：

```bash
curl -s http://127.0.0.1:8000/api/tasks/<task_id> | python -m json.tool
```

预期最终返回：

```json
{
  "status": "SUCCESS",
  "ready": true,
  "successful": true,
  "result": {
    "status": "ok",
    "message": "pong",
    "payload": {
      "source": "api"
    }
  },
  "error": null
}
```

更完整的本地 Redis / Celery 验收说明见 [docs/celery_redis_local.md](docs/celery_redis_local.md)。

## 12. 可选集成测试

```bash
RUN_CELERY_INTEGRATION=1 .venv/bin/python -m pytest tests/test_celery_redis_integration.py -v
```

说明：

- 默认 pytest 会跳过该测试。
- 只有 Redis 和 Celery worker 已启动时才运行。
- 该测试只验证 `ping_task`，不调用 LLM。

## 13. 环境变量

```text
INTERVIEWACE_DB_PATH
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
DEEPSEEK_API_KEY
```

- `INTERVIEWACE_DB_PATH` 默认使用 `data/interviews.db`。
- `CELERY_BROKER_URL` 默认 `redis://localhost:6379/0`。
- `CELERY_RESULT_BACKEND` 默认 `redis://localhost:6379/1`。
- `DEEPSEEK_API_KEY` 用于 `core/analyzer.py` 中的 DeepSeek / OpenAI-compatible LLM 调用。

## 14. 测试策略

- 默认测试不依赖 Redis。
- 默认测试不调用真实 LLM。
- API 测试使用 FastAPI `TestClient`。
- Celery `delay` / `AsyncResult` 在单元测试中使用 monkeypatch。
- 真实 Redis + worker 只用于可选集成验收。

## 15. 当前限制

- 当前知识库检索以 keyword / FTS 为主，尚未接入 embedding retriever。
- 当前没有实现模型微调。
- 当前异步任务结果主要依赖 Redis result backend，尚未落库持久化。
- 当前未实现任务取消 / revoke。
- 当前 SQLite 更适合本地和 MVP，生产环境可迁移到 MySQL / PostgreSQL。
- `preparation.generate_plan` 异步任务会调用真实 LLM，需要 API key、网络和代理配置正常。

## 16. Roadmap

- README 配套截图或接口示例图。
- Docker Compose 编排 API / worker / redis。
- `task_records` 表，持久化任务状态和结果。
- MySQL / PostgreSQL 数据库迁移。
- Embedding retriever + rerank。
- 更完整的 RAG citations。
- 面试准备计划 UI 接入。
- 异步任务状态前端轮询。
- Prompt evaluation golden cases 增强。
- JSON Schema 结构化 LLM 输出。

## 17. 项目协作指南

AI coding agent 开发规范见：

```text
AGENTS.md
```

如果使用 Claude Code：

```text
CLAUDE.md delegates to AGENTS.md.
```
