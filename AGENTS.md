# InterviewAce Agent Guide

## 1. Project Overview

InterviewAce 是一个 AI 面试复盘与准备系统。项目从讯飞听见导出的面试转写文本出发，完成解析、AI 复盘、历史沉淀、知识检索、证据引用和面试准备计划生成。

当前能力包括：

- 讯飞转写文本解析
- AI 面试话题分析
- full-context 面试分析
- 五维或多维能力诊断
- 历史记录保存
- 面试知识库 `knowledge_chunks`
- keyword / FTS 检索
- Evidence Context 构建
- 基于历史证据的准备计划生成
- FastAPI API 层
- Redis / Celery 异步任务化

## 2. Current Architecture

```text
Streamlit UI
  ↓
core / agent
  ↓
knowledge
  ↓
preparation
  ↓
api
  ↓
worker / Celery
```

目录职责：

- `app.py` / `pages/`：Streamlit UI 和多页面入口。
- `agent/`：现有 Agent Orchestrator 和 Tool 链路。
- `core/`：转写解析、DeepSeek 调用、SQLite 基础存储。
- `prompts/`：Prompt 模板、Prompt Builder、诊断维度配置。
- `knowledge/`：知识库数据模型、幂等索引、FTS/LIKE 检索、Evidence Context。
- `preparation/`：面试准备计划 request/result schema 和 service 编排。
- `api/`：FastAPI router、Pydantic schema、依赖注入和 HTTP 响应转换。
- `worker/`：Celery app、Celery task 和异步执行层。
- `tests/`：单元测试、API 测试、可选 integration test。
- `docs/`：本地集成和项目说明文档。
- `scripts/`：本地启动 API / Redis / Celery worker 的脚本。

## 3. Version Milestones

- V1：`knowledge_chunks` 数据模型  
  新增 `knowledge/` repository/service/schema，支持复盘结果沉淀为可追溯、可幂等写入的知识片段。

- V2：keyword / FTS 检索  
  新增 `knowledge/search.py`，优先使用 SQLite FTS5，不可用时 fallback 到 LIKE。

- V3：Evidence Context + 引用式 Prompt  
  新增 `knowledge/context_builder.py` 和 `prompts/evidence_based_advice.py`，将检索结果格式化为 `[E1]` 证据上下文。

- V4.1：Preparation Plan Prompt Builder  
  新增 `prompts/preparation_plan.py`，构建基于历史证据的面试准备计划 Prompt。

- V4.2：Evidence-based Preparation Service  
  新增 `preparation/`，编排 search → evidence context → prompt → LLM。

- V5：FastAPI API 化  
  新增 `api/`，暴露 health、knowledge search、evidence context、preparation plan 接口。

- V6.1：Celery 骨架 + 异步任务接口  
  新增 `worker/` 和 task API，支持提交 preparation plan 异步任务与查询状态。

- V6.2：Redis / Celery 本地真实集成验收支持  
  新增 ping task、本地启动脚本、Redis/Celery 集成文档和默认 skip 的 integration test。

## 4. Core Module Responsibilities

### core/

负责原始转写解析、AI 分析调用、SQLite 基础存储能力。`core/analyzer.py` 使用 OpenAI SDK 兼容方式调用 DeepSeek，API key 配置以该文件为准。

### agent/

负责现有 Agent Orchestrator 和 Tool 链路。不要把 API router、Celery task 或 knowledge 检索逻辑直接塞进 Agent。

### prompts/

负责 Prompt 模板与 Prompt Builder。Prompt Builder 只构造 Prompt，不调用 LLM，不访问数据库。

### knowledge/

负责知识库数据模型、索引、检索、Evidence Context。`repository` 只关心 `knowledge_chunks` 读写；`service` 从业务表构建 chunks；`search` 只做 keyword / FTS 检索。

### preparation/

负责面试准备计划 request/result schema 和 service 编排。该层复用 `knowledge.search`、`knowledge.context_builder` 和 `prompts.preparation_plan`，再调用通用 LLM 文本生成函数。

### api/

负责 FastAPI router、Pydantic schema、依赖注入和 HTTP 响应转换。API 层必须是薄封装，不写 SQL、不拼 Prompt、不直接调用 LLM client。

### worker/

负责 Celery app、Celery task 和异步执行层。task 必须是薄包装，接收 JSON 可序列化 dict，复用 service，不复制业务逻辑。

### tests/

负责单元测试、API 测试、可选 integration test。默认测试必须不依赖 Redis、Celery worker 或真实 LLM。

### scripts/

负责本地启动 API / Redis / Celery worker。脚本不得写入真实 API key 或用户本地绝对路径。

## 5. Development Principles

1. 高内聚、低耦合。
2. API 层必须是薄封装，不写 SQL、不拼 Prompt、不调用 LLM client。
3. worker task 必须是薄包装，复用 service，不复制业务逻辑。
4. service 层负责编排，不直接承担 UI/API 责任。
5. Prompt Builder 只构造 Prompt，不调用 LLM。
6. 测试中默认 mock LLM，不真实调用 DeepSeek/OpenAI compatible API。
7. 默认 pytest 不依赖 Redis / Celery worker。
8. Integration test 必须显式设置环境变量才运行。
9. 不要把大 prompt、evidence_context、完整 transcript 放入 Celery payload。
10. 不要在脚本或文档中写真实 API key。
11. 不要随意改数据库 schema。
12. 保留同步接口 `/api/preparation/plan`，同时提供异步接口 `/api/preparation/plan-tasks`。

## 6. API Endpoints

- `GET /api/health`：健康检查。
- `POST /api/knowledge/search`：检索 `knowledge_chunks`，返回 chunk 来源、snippet 和 score。
- `POST /api/knowledge/evidence-context`：检索后构建 `[E1]` 格式 Evidence Context，不调用 LLM。
- `POST /api/preparation/plan`：同步生成基于历史证据的面试准备计划。
- `POST /api/preparation/plan-tasks`：提交异步 preparation plan Celery task。
- `POST /api/tasks/ping`：提交轻量 ping task，用于 Redis / Celery 本地链路验收。
- `GET /api/tasks/{task_id}`：查询 Celery task 状态和结果。

## 7. Async Task Architecture

```text
FastAPI
  ↓
Celery delay
  ↓
Redis broker
  ↓
Celery worker
  ↓
preparation service
  ↓
Redis result backend
  ↓
GET /api/tasks/{task_id}
```

- Redis DB 0 默认作为 broker：`redis://localhost:6379/0`
- Redis DB 1 默认作为 result backend：`redis://localhost:6379/1`
- `system.ping` 用于本地集成验收，不调用 LLM，不访问数据库。
- `preparation.generate_plan` 会调用真实 LLM，因此不要作为默认自动测试。

## 8. Environment Variables

- `INTERVIEWACE_DB_PATH`：API 和 worker 使用的 SQLite DB 路径，默认 `data/interviews.db`。
- `CELERY_BROKER_URL`：Celery broker，默认 `redis://localhost:6379/0`。
- `CELERY_RESULT_BACKEND`：Celery result backend，默认 `redis://localhost:6379/1`。
- `DEEPSEEK_API_KEY`：DeepSeek API key，按 `core/analyzer.py` 当前配置使用。

LLM API key follows the existing `core/analyzer.py` configuration.

## 9. Common Commands

安装依赖：

```bash
.venv/bin/pip install -r requirements.txt
```

运行测试：

```bash
.venv/bin/python -m pytest tests/ -v
```

启动 API：

```bash
./scripts/run_api.sh
```

启动 worker：

```bash
./scripts/run_worker.sh
```

启动 Redis（Docker）：

```bash
./scripts/run_redis_docker.sh
```

启动 Redis（本地）：

```bash
brew install redis
./scripts/run_redis_local.sh
redis-cli ping
```

运行可选 integration test：

```bash
RUN_CELERY_INTEGRATION=1 .venv/bin/python -m pytest tests/test_celery_redis_integration.py -v
```

## 10. Testing Rules

- 默认测试必须不依赖 Redis。
- `tests/test_celery_redis_integration.py` 默认 skip。
- API 测试使用 FastAPI `TestClient`。
- preparation plan API 测试必须 mock LLM。
- Celery `delay` / `AsyncResult` 在单元测试中必须 monkeypatch。
- 真实 Redis + worker 只用于手动集成验收。
- 测试必须使用临时 SQLite DB，不污染 `data/interviews.db`。

## 11. Manual Verification Checklist

- `pytest` 通过。
- `/api/health` 返回 `ok`。
- `/api/knowledge/search` 返回 snippet 和 source_id。
- `/api/knowledge/evidence-context` 返回 `[E1]`。
- `/api/preparation/plan` 在测试中通过 mock LLM。
- `/api/preparation/plan-tasks` 返回 `202` 和 `task_id`。
- `/api/tasks/ping` 在真实 Redis 环境下最终 `SUCCESS`。
- `/api/tasks/{task_id}` 能展示 `PENDING` / `SUCCESS` / `FAILURE`。
- worker 日志能看到 `system.ping` received / succeeded。

## 12. Boundaries and Do-Not-Change Rules

- 不要把 Agent、API、worker、knowledge、preparation 混在一起。
- 不要在 router 里写 SQL。
- 不要在 router 里拼 Prompt。
- 不要在 worker 里复制 service 逻辑。
- 不要让默认 pytest 依赖真实 Redis。
- 不要在默认测试中调用真实 LLM。
- 不要把 API key 写入仓库。
- 不要把 `data/interviews.db`、`.env`、缓存文件提交。
- 不要随意改已有数据库 schema。
- 不要删除同步 preparation 接口。
- 不要把 integration test 变成默认必跑。

## 13. Next Roadmap

以下只是规划，本文件更新不代表本轮要实现：

- 更新 `README.md`，对外展示项目价值。
- 增加 `task_records` 表，持久化任务状态和结果。
- Docker Compose 编排 API / worker / Redis。
- MySQL 替换 SQLite。
- Redis 缓存检索结果。
- 更完整的 RAG：embedding retriever / rerank / citations。
- 更完整的评测系统：golden case、LLM 输出结构化、自动评分。
- UI 接入异步任务状态。
