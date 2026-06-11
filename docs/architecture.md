# InterviewAce Architecture

## 1. Architecture Overview

InterviewAce 从 Streamlit MVP 演进为支持知识库检索、Evidence Context、FastAPI API 和 Celery 异步任务的 AI 面试复盘与准备系统。

当前架构分为 UI 层、核心分析层、知识库层、准备计划层、API 层、异步任务层和测试层。系统重点不是简单调用 LLM，而是把“面试转写 -> 复盘分析 -> 知识沉淀 -> 证据检索 -> 准备计划”串成可测试、可服务化的闭环。

## 2. Overall System Architecture

```mermaid
flowchart TD
    U["User / Interview Transcript"] --> UI["Streamlit UI<br/>app.py / pages/"]

    UI --> Agent["Agent Orchestrator<br/>agent/"]
    UI --> Core["Core Analysis<br/>core/"]

    Agent --> Tools["Agent Tools<br/>parse / group / analyze / summarize / score / save"]
    Tools --> Core

    Core --> Prompts["Prompt Builders<br/>prompts/"]
    Core --> Storage["SQLite Storage<br/>sessions / turns / questions"]

    Storage --> KB["Knowledge Base<br/>knowledge_chunks"]
    KB --> Search["Keyword / FTS Search<br/>knowledge/search.py"]
    Search --> Evidence["Evidence Context<br/>[E1] / [E2] / [E3]"]

    Evidence --> Prep["Preparation Service<br/>preparation/service.py"]
    Prompts --> Prep

    Prep --> LLM["LLM Provider<br/>DeepSeek / OpenAI-compatible API"]

    API["FastAPI API<br/>api/"] --> Search
    API --> Evidence
    API --> Prep

    API --> CelerySubmit["Submit Async Task<br/>/api/preparation/plan-tasks"]
    CelerySubmit --> RedisBroker["Redis Broker<br/>DB 0"]
    RedisBroker --> Worker["Celery Worker<br/>worker/"]
    Worker --> Prep
    Worker --> RedisResult["Redis Result Backend<br/>DB 1"]
    API --> TaskStatus["Task Status API<br/>/api/tasks/{task_id}"]
    TaskStatus --> RedisResult
```

说明：

- Streamlit 是原始 MVP UI，用于本地上传转写和查看复盘结果。
- FastAPI 是服务化接口层，对外提供检索、证据上下文、准备计划和任务状态接口。
- `knowledge/` 负责历史复盘知识沉淀、幂等索引和 keyword / FTS 检索。
- `preparation/` 负责基于 evidence 生成准备计划。
- `worker/` 负责异步执行长耗时 LLM 任务。
- Redis DB 0 默认作为 broker，Redis DB 1 默认作为 result backend。

## 3. Interview Review Flow

```mermaid
flowchart TD
    A["Interview Transcript<br/>讯飞转写 / 文本记录"] --> B["Parse Interview<br/>提取问题与回答"]
    B --> C{"Analysis Mode"}

    C -->|topic-based| D["Group Topics<br/>话题分组"]
    D --> E["Analyze Topics<br/>逐话题复盘"]

    C -->|full-context| F["Full-context Analysis<br/>完整上下文复盘"]

    E --> G["Generate Summary<br/>整体总结"]
    F --> G

    G --> H["Score Performance<br/>能力评分 / 诊断"]
    H --> I["Save Results<br/>sessions / turns / questions"]
    I --> J["Build Knowledge Chunks<br/>session_summary / turn_feedback / question_bank"]
```

说明：

- topic-based 保留原有分组分析能力。
- full-context 利用长上下文模型减少跨轮信息丢失。
- 分析结果保存到 `sessions`、`turns`、`questions` 后，可以进一步沉淀为 `knowledge_chunks`。

## 4. Evidence-based RAG Flow

当前 RAG 链路是 keyword / SQLite FTS 检索 + Evidence Context，不是 embedding retriever，也没有实现向量数据库或 rerank。

```mermaid
flowchart TD
    A["sessions / turns / questions"] --> B["Build Knowledge Chunks<br/>knowledge/service.py"]
    B --> C["knowledge_chunks<br/>SQLite Table"]

    C --> D["Keyword / FTS Search<br/>knowledge/search.py"]
    D --> E["Search Results<br/>KnowledgeSearchResult"]

    E --> F["Build Evidence Blocks<br/>EvidenceContextBlock"]
    F --> G["Format Evidence Context<br/>[E1] [E2] [E3]"]

    G --> H["Evidence-based Prompt<br/>must cite evidence id"]
    H --> I["LLM Output<br/>Advice / Preparation Plan"]
```

防幻觉约束：

- 每条证据有稳定编号，例如 `[E1]`。
- 历史表现判断必须引用证据编号。
- 证据不足必须写“历史证据不足”。
- 不能把“建议补充展示”写成“候选人已经做到”。
- 空 evidence 时不允许生成具体历史表现判断。

## 5. Preparation Plan Generation Flow

```mermaid
sequenceDiagram
    participant Client
    participant Service as Preparation Service
    participant Search as Knowledge Search
    participant Evidence as Evidence Context Builder
    participant Prompt as Preparation Prompt Builder
    participant LLM as LLM Provider

    Client->>Service: user_goal / job_direction / query
    Service->>Search: search_knowledge_chunks(query, top_k)
    Search-->>Service: KnowledgeSearchResult[]
    Service->>Evidence: build_evidence_context(results)
    Evidence-->>Service: evidence_context with [E1]/[E2]
    Service->>Prompt: build_preparation_plan_prompt(...)
    Prompt-->>Service: prompt
    Service->>LLM: generate_text(prompt)
    LLM-->>Service: preparation plan
    Service-->>Client: PreparationPlanResult
```

说明：

- `preparation.service` 只负责编排 search -> evidence -> prompt -> LLM。
- Prompt Builder 只构造 Prompt，不调用 LLM。
- Search / Evidence / Prompt 逻辑不复制到 API 层。

## 6. FastAPI Layer

```mermaid
flowchart LR
    Client["HTTP Client / Frontend / curl"] --> API["FastAPI<br/>api/main.py"]

    API --> Health["GET /api/health"]
    API --> SearchAPI["POST /api/knowledge/search"]
    API --> EvidenceAPI["POST /api/knowledge/evidence-context"]
    API --> PlanAPI["POST /api/preparation/plan"]
    API --> PlanTaskAPI["POST /api/preparation/plan-tasks"]
    API --> PingAPI["POST /api/tasks/ping"]
    API --> StatusAPI["GET /api/tasks/{task_id}"]

    SearchAPI --> Search["knowledge/search.py"]
    EvidenceAPI --> Context["knowledge/context_builder.py"]
    PlanAPI --> Prep["preparation/service.py"]
    PlanTaskAPI --> Celery["Celery Task Queue"]
    PingAPI --> Celery
    StatusAPI --> ResultBackend["Redis Result Backend"]
```

说明：

- API 层只做请求校验、依赖获取和响应转换。
- Router 不写 SQL。
- Router 不拼 Prompt。
- Router 不直接初始化 LLM client。

## 7. Celery / Redis Async Task Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI API
    participant RedisB as Redis Broker DB 0
    participant Worker as Celery Worker
    participant Prep as Preparation Service
    participant RedisR as Redis Result Backend DB 1

    Client->>API: POST /api/preparation/plan-tasks
    API->>RedisB: generate_preparation_plan_task.delay(payload)
    API-->>Client: 202 Accepted + task_id

    RedisB->>Worker: deliver task
    Worker->>Prep: generate_preparation_plan(...)
    Prep-->>Worker: PreparationPlanResult
    Worker->>RedisR: store result

    Client->>API: GET /api/tasks/{task_id}
    API->>RedisR: query AsyncResult
    RedisR-->>API: PENDING / SUCCESS / FAILURE
    API-->>Client: TaskStatusResponse
```

Ping task 验收链路：

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI API
    participant RedisB as Redis Broker
    participant Worker as Celery Worker
    participant RedisR as Redis Result Backend

    Client->>API: POST /api/tasks/ping
    API->>RedisB: system.ping.delay({"source": "api"})
    API-->>Client: 202 Accepted + task_id

    RedisB->>Worker: system.ping
    Worker->>Worker: run_ping_task()
    Worker->>RedisR: {"status":"ok","message":"pong"}

    Client->>API: GET /api/tasks/{task_id}
    API->>RedisR: AsyncResult(task_id)
    API-->>Client: SUCCESS + pong
```

说明：

- `system.ping` 用于验证 Redis -> Worker -> Result Backend，不调用 LLM。
- `preparation.generate_plan` 会调用真实 LLM，不作为默认自动测试。
- 默认 pytest 不依赖 Redis。

## 8. Module Responsibility Map

| Module | Responsibility |
|---|---|
| `app.py / pages/` | Streamlit MVP UI |
| `core/` | Transcript parsing, LLM analysis, storage |
| `agent/` | Agent orchestrator and tool chain |
| `prompts/` | Prompt templates and prompt builders |
| `knowledge/` | `knowledge_chunks`, repository, search, evidence context |
| `preparation/` | Preparation request/result schema and service orchestration |
| `api/` | FastAPI routers, Pydantic schemas, HTTP response conversion |
| `worker/` | Celery app and async task execution |
| `tests/` | Unit tests, API tests, optional integration tests |
| `scripts/` | Local startup scripts |
| `docs/` | Project documentation |

## 9. Testing Architecture

```mermaid
flowchart TD
    T["pytest tests/"] --> Unit["Unit Tests"]
    T --> API["API Tests<br/>FastAPI TestClient"]
    T --> Prompt["Prompt Builder Tests"]
    T --> Worker["Worker Task Tests"]
    T --> Optional["Optional Integration Tests"]

    Unit --> MockLLM["Mock LLM<br/>no real API call"]
    API --> MockCelery["Mock Celery delay / AsyncResult"]
    Worker --> MockService["Mock preparation service"]
    Optional --> Redis["Real Redis + Celery Worker<br/>RUN_CELERY_INTEGRATION=1"]

    Redis --> Ping["system.ping only<br/>no LLM"]
```

说明：

- 默认测试不调用真实 LLM。
- 默认测试不依赖 Redis。
- Integration test 默认 skip。
- 真实 Redis + worker 验证通过 `system.ping` 完成。

## 10. Current Limitations

- 当前 RAG 主要是 keyword / SQLite FTS，不是 embedding retriever。
- 当前未实现 rerank。
- 当前未实现模型微调。
- 当前 LLM 输出主要是 Markdown，后续可做 JSON Schema 结构化输出。
- 当前异步任务结果主要依赖 Redis result backend，尚未持久化到 `task_records` 表。
- 当前 SQLite 适合 MVP 和本地演示，生产可迁移 MySQL / PostgreSQL。
- 当前没有完整用户系统和权限控制。

## 11. Roadmap Architecture

这部分是后续架构方向，不代表当前已经实现。

```mermaid
flowchart TD
    A["Current System"] --> B["Structured Output<br/>JSON Schema"]
    B --> C["Task Records<br/>Persist async results"]
    C --> D["Docker Compose<br/>api / worker / redis"]
    D --> E["Database Migration<br/>MySQL / PostgreSQL"]
    E --> F["Embedding Retriever<br/>Hybrid Retrieval"]
    F --> G["Rerank + Stronger Citations"]
    G --> H["Frontend Async Task UI"]
```
