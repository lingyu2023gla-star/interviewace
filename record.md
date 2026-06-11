# InterviewAce · 项目记录文档

> 用于跨对话延续项目上下文，记录项目背景、当前结构、已完成功能、运行方式、已知问题和下一步方向。  
> 这是内部项目记录，不替代 README、AGENTS.md 或面试讲解文档。

---

## 1. 项目定位

InterviewAce 是一个 AI 面试复盘与准备系统。项目从 Streamlit MVP 起步，逐步演进为包含知识库、Evidence Context、结构化输出、FastAPI API、Celery/Redis 异步任务和 Docker Compose 本地开发栈的后端大模型应用。

核心闭环：

```text
面试转写文本
  -> 解析问题与回答
  -> topic-based / full-context 分析
  -> 能力诊断与反馈生成
  -> 保存 sessions / turns / questions
  -> 沉淀 knowledge_chunks
  -> keyword / FTS 检索
  -> 构建 Evidence Context：[E1] / [E2]
  -> 生成基于历史证据的准备计划
  -> FastAPI / Celery 对外提供服务
```

当前项目强调：

- 面试复盘质量：区分能力不足、证据不足、覆盖缺口。
- 防幻觉：历史表现判断必须基于 Evidence Context。
- 后端工程化：API 层、service 层、worker 层职责分离。
- 测试稳定性：默认测试不依赖真实 LLM、Redis、Celery worker 或 Docker。

---

## 2. 当前基础信息

| 项目 | 信息 |
|---|---|
| 项目名 | InterviewAce |
| 本地路径 | `/Users/apple/workspace/yuling/interviewace` |
| Python | 当前 `.venv` 使用 Python 3.14.0 |
| UI | Streamlit |
| API | FastAPI |
| AI 调用 | DeepSeek / OpenAI-compatible API |
| 存储 | SQLite |
| 异步任务 | Celery |
| Broker / Result Backend | Redis |
| 默认数据库 | `data/interviews.db` |
| 测试命令 | `.venv/bin/python -m pytest tests/ -v` |
| 当前测试结果 | `210 passed, 2 skipped` |

常用启动命令：

```bash
streamlit run app.py
./scripts/run_api.sh
./scripts/run_worker.sh
./scripts/run_redis_local.sh
docker compose up --build
```

---

## 3. 当前目录结构快照

```text
interviewace/
├── app.py                         # Streamlit 主入口
├── pages/                         # Streamlit 多页面
│   ├── growth.py
│   ├── mock_interview.py
│   ├── practice_plan.py
│   └── question_bank.py
├── agent/                         # Agent Orchestrator 与 Tool 链路
│   ├── orchestrator.py
│   ├── schemas.py
│   └── tools.py
├── core/                          # 转写解析、LLM 调用、基础存储
│   ├── analyzer.py
│   ├── parser.py
│   └── storage.py
├── prompts/                       # Prompt 模板与 Prompt Builder
│   ├── dimensions.py
│   ├── evidence_based_advice.py
│   ├── interview_analysis.py
│   ├── preparation_plan.py
│   └── structured_preparation_plan.py
├── knowledge/                     # knowledge_chunks、检索、Evidence Context
│   ├── context_builder.py
│   ├── repository.py
│   ├── schemas.py
│   ├── search.py
│   └── service.py
├── preparation/                   # 准备计划 schema、service、structured output
│   ├── schemas.py
│   ├── service.py
│   ├── structured_parser.py
│   ├── structured_schemas.py
│   └── structured_service.py
├── api/                           # FastAPI app、schemas、routers
│   ├── deps.py
│   ├── main.py
│   ├── schemas.py
│   └── routers/
├── worker/                        # Celery app、tasks、task_records
│   ├── celery_app.py
│   ├── task_records.py
│   └── tasks.py
├── integrations/gbrain/           # GBrain-friendly Markdown export adapter
├── scripts/                       # 本地启动与评测脚本
├── docs/                          # 架构、面试讲解、本地集成文档
├── tests/                         # 单元测试、API 测试、可选 integration 测试
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── README.md
├── AGENTS.md
└── record.md
```

运行生成物和本地数据：

- `data/interviews.db`：SQLite 数据库，本地运行生成。
- `outputs/eval/`：Prompt 质量评测输出。
- `exports/gbrain/`：GBrain Markdown 导出结果。
- `dump.rdb`：本地 Redis 运行可能生成的快照文件。

这些运行时文件不应作为核心源码能力来理解。

---

## 4. 已完成版本里程碑

| 阶段 | 能力 | 关键文件 |
|---|---|---|
| MVP | Streamlit 面试复盘、历史记录、题库、成长追踪 | `app.py`, `core/`, `pages/` |
| Agent | Orchestrator + ToolResult 工具链 | `agent/orchestrator.py`, `agent/tools.py` |
| Full Context | 完整上下文分析 Prompt Builder | `prompts/interview_analysis.py`, `core/analyzer.py` |
| V1 | `knowledge_chunks` 数据模型与幂等索引 | `knowledge/repository.py`, `knowledge/service.py` |
| V2 | keyword / FTS 检索，LIKE fallback | `knowledge/search.py` |
| V3 | Evidence Context 与引用式 Prompt | `knowledge/context_builder.py`, `prompts/evidence_based_advice.py` |
| V4.1 | Preparation Plan Prompt Builder | `prompts/preparation_plan.py` |
| V4.2 | Preparation Service：search -> evidence -> prompt -> LLM | `preparation/service.py` |
| V5 | FastAPI API 化 | `api/` |
| V6.1 | Celery 骨架与异步任务接口 | `worker/celery_app.py`, `worker/tasks.py` |
| V6.2 | Redis/Celery 本地集成验收支持 | `scripts/`, `docs/celery_redis_local.md` |
| V7.1 | Structured Preparation Plan schema/parser/service | `preparation/structured_*`, `prompts/structured_preparation_plan.py` |
| V7.2 | Structured Output 同步 API | `POST /api/preparation/structured-plan` |
| V8.1 | GBrain Markdown Export Adapter | `integrations/gbrain/` |
| V8.2 | SQLite `task_records` 异步任务持久化 | `worker/task_records.py` |
| V8.3 | Docker Compose 本地开发栈 | `Dockerfile`, `docker-compose.yml`, `docs/docker_compose.md` |

---

## 5. 主要功能实现

### 5.1 面试复盘主链路

- 支持讯飞听见 `.txt` 转写文本解析。
- 支持说话人角色映射。
- 支持面试官问题与候选人回答配对。
- 支持 topic-based 分组分析。
- 支持 full-context 完整上下文分析。
- 支持整体总结、能力评分、题库沉淀和历史记录保存。

核心模块：

- `core/parser.py`
- `core/analyzer.py`
- `core/storage.py`
- `agent/orchestrator.py`
- `agent/tools.py`

### 5.2 Prompt 体系

当前 Prompt 能力包括：

- 单话题分析 Prompt
- 整体总结 Prompt
- 话题分组 JSON Prompt
- 能力评分 JSON Prompt
- full-context 分析 Jinja2 Prompt
- Evidence-based advice Prompt
- Preparation Plan Prompt
- Structured Preparation Plan JSON-only Prompt

能力诊断维度已从 full-context Prompt 主体中抽离：

- `prompts/dimensions.py`
- `DiagnosisDimension`
- `DEFAULT_LLM_APP_DIMENSIONS`
- `build_full_context_analysis_prompt(...)`

### 5.3 Knowledge Base

新增独立 `knowledge/` 模块，不修改原有 `sessions / turns / questions` 表结构。

核心表：

```sql
knowledge_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    session_id INTEGER,
    turn_id INTEGER,
    question_id INTEGER,
    title TEXT,
    content TEXT NOT NULL,
    job_direction TEXT,
    topic TEXT,
    dimension_key TEXT,
    tags TEXT,
    metadata_json TEXT,
    content_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

索引能力：

- session_id
- source_type + source_id
- topic
- dimension_key
- job_direction

幂等性依赖：

- `compute_content_hash(source_type, source_id, content)`
- 重复索引相同 chunk 时 skipped，不重复插入。

### 5.4 Keyword / FTS Search

`knowledge/search.py` 提供 `search_knowledge_chunks(...)`：

- 优先使用 SQLite FTS5。
- FTS5 不可用或查询失败时 fallback 到 LIKE。
- 支持过滤：
  - `session_id`
  - `source_type`
  - `topic`
  - `dimension_key`
  - `top_k`
- 返回 `KnowledgeSearchResult`，包含来源、snippet、score、tags、metadata。

当前不是 embedding RAG，也没有 rerank。

### 5.5 Evidence Context

`knowledge/context_builder.py` 将检索结果格式化为引用证据：

```text
[E1]
来源类型：turn_feedback
来源ID：turn:1:feedback
会话ID：1
主题：Agent 架构
维度：agent_architecture
标题：Agent 架构复盘
证据内容：
...
```

防幻觉规则：

- 历史表现判断必须引用 `[E1]` / `[E2]`。
- 证据不足必须写“历史证据不足”。
- 空 evidence 时不能生成具体历史表现判断。
- 不能把规划中或建议补充展示的能力写成已经完成。

### 5.6 Preparation Plan

Markdown 版本：

- Prompt Builder：`prompts/preparation_plan.py`
- Service：`preparation/service.py`
- API：`POST /api/preparation/plan`
- Async API：`POST /api/preparation/plan-tasks`

结构化 JSON 版本：

- Schema：`preparation/structured_schemas.py`
- Parser：`preparation/structured_parser.py`
- Prompt Builder：`prompts/structured_preparation_plan.py`
- Service：`preparation/structured_service.py`
- API：`POST /api/preparation/structured-plan`
- Async API：`POST /api/preparation/structured-plan-tasks`

结构化输出顶层字段：

- `summary`
- `evidence_based_judgments`
- `daily_plan`
- `question_templates`
- `abilities_to_show`
- `risk_warnings`
- `metadata`

### 5.7 FastAPI API

当前接口：

| Method | Path | 用途 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| POST | `/api/knowledge/search` | 知识库检索 |
| POST | `/api/knowledge/evidence-context` | 构建 Evidence Context |
| POST | `/api/preparation/plan` | 同步 Markdown 准备计划 |
| POST | `/api/preparation/structured-plan` | 同步结构化 JSON 准备计划 |
| POST | `/api/preparation/plan-tasks` | 异步 Markdown 准备计划任务 |
| POST | `/api/preparation/structured-plan-tasks` | 异步结构化准备计划任务 |
| POST | `/api/tasks/ping` | Celery ping task |
| GET | `/api/tasks/{task_id}` | 查询任务状态和 task_record |

API 层原则：

- 只做请求校验、依赖获取、响应转换。
- 不写 SQL。
- 不拼 Prompt。
- 不直接调用 LLM client。

### 5.8 Celery / Redis / task_records

Celery 配置：

- `worker/celery_app.py`
- broker 默认：`redis://localhost:6379/0`
- result backend 默认：`redis://localhost:6379/1`

Celery task：

- `system.ping`
- `preparation.generate_plan`
- `preparation.generate_structured_plan`

SQLite `task_records` 表：

```sql
task_records (
    task_id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL,
    status TEXT NOT NULL,
    request_json TEXT,
    result_json TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    updated_at TEXT NOT NULL
)
```

状态流转：

```text
PENDING -> STARTED -> SUCCESS
PENDING -> STARTED -> FAILURE
```

关系：

- Redis result backend 仍用于 Celery 原生状态。
- `task_records` 用于长期保存请求、结果和失败原因。
- `GET /api/tasks/{task_id}` 同时返回 Celery 状态和数据库 task_record。

### 5.9 GBrain Markdown Export

`integrations/gbrain/` 支持将 `knowledge_chunks` 导出为 GBrain-friendly Markdown。

导出结构：

```text
exports/gbrain/
├── index.md
├── interviews/
├── topics/
└── chunks/
```

CLI：

```bash
.venv/bin/python -m integrations.gbrain.cli --db data/interviews.db --out exports/gbrain
```

当前只做 Markdown 导出：

- 不调用 GBrain CLI。
- 不接 MCP。
- 不调用 LLM。
- 不修改数据库。

### 5.10 Docker Compose Local Dev Stack

当前已新增：

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `docs/docker_compose.md`
- `tests/test_docker_compose_config.py`
- `tests/test_docker_compose_ci.py`

Compose 服务：

- `redis`
- `api`
- `worker`

启动方式：

```bash
docker compose up --build
```

后台启动：

```bash
docker compose up -d --build
```

可选 CI-only 配置检查：

```bash
RUN_DOCKER_COMPOSE_CHECK=1 .venv/bin/python -m pytest tests/test_docker_compose_ci.py -v
```

该检查只运行 `docker compose config`，不 build、不启动容器。

---

## 6. 测试现状

默认测试命令：

```bash
.venv/bin/python -m pytest tests/ -v
```

当前结果：

```text
210 passed, 2 skipped
```

默认 skip：

- `tests/test_celery_redis_integration.py`
  - 需要 `RUN_CELERY_INTEGRATION=1`
  - 需要真实 Redis + Celery worker
- `tests/test_docker_compose_ci.py`
  - 需要 `RUN_DOCKER_COMPOSE_CHECK=1`
  - 需要 Docker CLI

测试覆盖方向：

- parser
- analyzer 解析/降级
- storage
- orchestrator
- prompt builder
- eval fixture
- knowledge repository/service/search
- evidence context
- preparation service
- structured preparation parser/service
- FastAPI endpoints
- Celery worker task 普通函数
- task_records
- GBrain exporter
- Docker Compose 配置静态检查

---

## 7. 当前 Docker 状态记录

本机已安装 Docker CLI / Docker Desktop 后，`docker compose version` 可用：

```text
Docker Compose version v5.1.4
```

此前遇到的问题：

1. `docker compose up --build` 报 `unknown flag: --build`
   - 原因：Docker CLI 未识别 Compose 插件。
   - 处理：将 Docker Desktop 的 compose 插件链接到 `~/.docker/cli-plugins/docker-compose`。

2. Docker Engine 未启动时报：
   - `failed to connect to the docker API`
   - `permission denied while trying to connect to the docker API`
   - 处理：启动 Docker Desktop，等待 Engine 就绪。

3. 当前最新报错：

```text
failed to resolve reference "docker.io/library/redis:7-alpine"
context deadline exceeded
```

分析：

- Compose 文件本身可解析。
- Docker / Compose 已工作到拉取镜像阶段。
- 失败点是访问 Docker Hub 超时，常见原因是网络、代理或 Docker Desktop daemon 未配置代理。

验证命令：

```bash
docker pull redis:7-alpine
```

如果同样超时，说明问题不在项目配置，而在 Docker Hub 网络访问。

可选处理：

- 在 Docker Desktop 配置代理后重启 Docker。
- 换可访问的 Redis 镜像源。
- 临时不用 Docker Redis，改用本地 Redis：

```bash
./scripts/run_redis_local.sh
./scripts/run_worker.sh
./scripts/run_api.sh
```

---

## 8. 重要设计边界

- 不在默认测试中调用真实 LLM。
- 不让默认 pytest 依赖 Redis、Celery worker 或 Docker。
- 不把 API key 写入仓库。
- 不把大 prompt、完整 transcript、evidence_context 放入 Celery payload。
- API router 不写 SQL、不拼 Prompt、不直接调用 LLM。
- worker task 不复制业务逻辑，只包装 service。
- Prompt Builder 只构造 Prompt，不调用 LLM。
- 当前检索是 keyword / FTS，不是 embedding retriever。
- 当前没有实现 rerank。
- 当前没有实现模型微调。
- 当前 SQLite 更适合本地 MVP，生产可迁移 MySQL/PostgreSQL。

---

## 9. 当前面试讲解要点

### 1 分钟版本

我做的 InterviewAce 是一个 AI 面试复盘与准备系统，最初是 Streamlit MVP，后来逐步演进成带知识库、证据链、FastAPI 接口和 Celery 异步任务的后端大模型应用。核心流程是先解析面试转写，生成结构化复盘，再把复盘结果沉淀成 `knowledge_chunks`，通过 keyword/FTS 检索构建 `[E1]`、`[E2]` 这样的 Evidence Context，最后让模型基于历史证据生成下一次准备计划。为了减少幻觉，我在 Prompt 里要求所有历史表现判断必须引用证据编号，证据不足就明确写“历史证据不足”，不能把规划中的能力包装成已完成能力。工程上我用 FastAPI 暴露检索和准备计划接口，用 Celery/Redis 把 LLM 长任务异步化，并用 mock LLM、mock Celery 和可选 Redis integration test 保证默认测试稳定。

### 可展开亮点

- Agent Orchestrator + ToolResult 统一错误处理。
- full-context Prompt 支持多维能力诊断。
- Jinja2 动态注入诊断维度，提高 Prompt 可维护性。
- `knowledge_chunks` 幂等写入，便于长期沉淀。
- Evidence Context 强制引用历史证据，降低模型幻觉。
- Structured Output 支持 JSON schema/parser/service/API。
- task_records 让异步任务状态不只依赖 Redis 短期结果。
- Docker Compose 提供本地 API / worker / Redis 开发栈。

---

## 10. 当前限制

- 当前 RAG 主要是 keyword / SQLite FTS，不是 embedding RAG。
- 当前未实现 rerank。
- 当前未实现模型微调。
- 当前没有完整用户系统和权限控制。
- 当前异步任务结果虽已落 `task_records`，但还没有完整管理后台。
- 当前 Docker Compose 依赖 Docker Hub 拉取 `redis:7-alpine`，国内网络可能需要代理或镜像源。
- preparation task 调用真实 LLM 时需要 API key、网络和代理配置正常。

---

## 11. 下一步方向

短期：

- 解决 Docker Hub 拉取超时问题：配置 Docker Desktop proxy 或切换 Redis 镜像源。
- 完成一次 Docker Compose ping task 手动验收。
- 根据最新 V7/V8 能力同步 README、project_pitch、architecture、AGENTS 的差异点。

中期：

- `task_records` 查询列表 API。
- Docker Compose 加入 healthcheck 更完整的 API/worker 验收。
- Structured Output 接入更多分析报告。
- Prompt evaluation golden cases 增强。

长期：

- Docker Compose 编排 API / worker / redis / database 更完整环境。
- MySQL / PostgreSQL 替换 SQLite。
- Embedding retriever + hybrid retrieval。
- Rerank。
- 更完整的 citations。
- UI 接入异步任务状态。
- 面试准备计划长期追踪。
