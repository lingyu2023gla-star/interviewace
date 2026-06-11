# InterviewAce 项目面试说明

## 1. 一句话介绍

InterviewAce 是一个 AI 面试复盘与准备系统。它可以从面试转写文本中提取问题与回答，进行结构化复盘、能力诊断、知识库沉淀，并基于历史面试证据生成下一次面试准备计划。

这个项目最初是一个 Streamlit MVP，后来逐步演进为包含 Agent 链路、knowledge_chunks 知识库、Evidence Context、FastAPI 接口、Redis/Celery 异步任务和结构化 JSON 输出的后端大模型应用。

## 2. 项目背景与问题

传统面试复盘有几个明显问题：

- 面试结束后容易遗忘关键问题、回答细节和追问上下文。
- 人工复盘很难稳定发现表达结构、技术深度和岗位匹配问题。
- 普通 LLM 直接总结容易产生幻觉，可能把候选人没有展示过的能力写成已经具备。
- 面试准备如果脱离历史表现，往往只能得到泛泛建议，不能指导下一次怎么补强。

InterviewAce 主要解决四件事：

- 把原始面试转写变成可复盘的数据。
- 把历史复盘结果沉淀为可检索、可追溯的知识库。
- 通过检索历史证据，生成有依据的准备建议。
- 通过 FastAPI 和 Celery/Redis 把能力服务化，支持同步和异步调用。

## 3. 核心业务流程

```text
面试转写文本
  ↓
解析问题与回答
  ↓
full-context / topic-based 分析
  ↓
能力诊断与反馈生成
  ↓
保存历史记录与题库
  ↓
沉淀 knowledge_chunks
  ↓
keyword / FTS 检索
  ↓
构建 Evidence Context：[E1] / [E2]
  ↓
生成基于历史证据的准备计划
  ↓
结构化 JSON 输出 / Markdown 输出
  ↓
FastAPI / Celery 异步任务对外提供能力
```

## 4. 我的主要技术工作

### 4.1 面试复盘 Agent 链路

我设计了 Agent Orchestrator 和统一的 `ToolResult` 返回结构，把一次面试复盘拆成解析、分组、分析、总结、评分和保存等独立工具。

这个设计的重点不是把所有逻辑写成一个大函数，而是让每个 Tool 有明确输入输出，Orchestrator 负责流程控制和降级策略。例如 topic 分组失败时可以退化为逐轮分析，评分失败时可以跳过评分但不阻断主报告保存。

当前系统同时保留了 topic-based 和 full-context 两种分析模式：前者适合按话题拆解，后者适合利用现代 LLM 长上下文能力做完整面试诊断。

### 4.2 Full-context 分析模式

我新增了 full-context 分析模式，核心原因是面试里的同一能力点经常散落在多轮追问中。如果过度切分成单轮问答，模型容易丢失跨轮上下文，导致判断片面。

在 Prompt 设计上，我要求模型区分三类情况：

- 能力不足：回答错误、过浅、混乱或缺少实践细节。
- 证据不足：本场没有问到，或候选人没有展开。
- 覆盖缺口：目标岗位需要该能力，但本场没有充分展示。

未被问到的能力不强行扣分，而是标记为“未验证 / N/A”。这能降低误判，也让复盘建议更可信。

### 4.3 知识库与 Evidence-based RAG

我设计了 `knowledge_chunks` 数据模型，用来把复盘结果沉淀为可检索、可追溯、可幂等写入的知识片段。

当前会把 session summary、turn feedback、question bank 等内容构造成 chunk，并记录来源类型、来源 ID、session、turn、question、topic、dimension、tags、metadata 和 content hash。content hash 用于保证重复索引不会重复插入。

检索层实现了 keyword / SQLite FTS5 搜索，并在 FTS5 不可用或查询失败时 fallback 到 LIKE 检索。需要强调的是：当前是 keyword / FTS + Evidence Context，不是已经完成 embedding retriever 或向量数据库 RAG。

检索结果会被格式化为 Evidence Context，每条证据有稳定编号，例如 `[E1]`、`[E2]`。后续 Prompt 强制模型的历史表现判断必须引用证据编号；如果证据不足，必须明确说“历史证据不足”。

### 4.4 基于历史证据的准备计划

我设计了 preparation plan prompt builder 和 service。它会根据用户目标、岗位方向和历史 Evidence Context，生成下一阶段面试准备计划。

准备计划不是泛泛写“加强学习”，而是要求包含：

- 准备重点判断。
- 每日任务和预计时间。
- 重点问题回答模板。
- 历史证据不足但需要主动展示的能力。
- 过度包装风险提醒。

这里的关键是区分“已有证据支持”和“需要下次主动展示”。例如 RAG 如果只是规划中，就不能写成已经完整实现；微调如果没有落地，也不能包装成项目经验。

### 4.5 Structured Output / JSON Schema

在 V7 阶段，我为 preparation plan 增加了结构化 JSON 输出能力，但没有替换旧的 Markdown 输出。

具体做法是：

- 定义 `StructuredPreparationPlan` Pydantic schema，包含 summary、evidence_based_judgments、daily_plan、question_templates、abilities_to_show、risk_warnings 和 metadata。
- 新增 JSON-only Prompt Builder，要求模型只输出 JSON，不输出 Markdown 或额外解释。
- 新增 parser，支持纯 JSON、Markdown fenced JSON 和前后带文本的 JSON 提取。
- 使用 Pydantic 校验模型输出，非法 JSON 或缺少字段时抛出明确错误。
- 新增同步 API `/api/preparation/structured-plan`，返回可被前端直接渲染和后续持久化的结构化结果。

这个能力的价值是让准备计划从“可读 Markdown”进一步变成“可展示、可测试、可存储、可统计”的结构化数据。当前结构化输出先支持 preparation plan，尚未覆盖所有复盘报告，也还没有接入 Celery 异步任务。

### 4.6 FastAPI 服务化

我把知识检索、Evidence Context 和准备计划能力封装成 FastAPI 接口。

API 层保持薄封装，只做请求校验、service 调用和响应转换，不写 SQL、不拼 Prompt、不直接调用 LLM client。请求参数用 Pydantic 校验，非法输入返回 422，并通过 `/docs` 自动生成 OpenAPI 文档。

结构化准备计划 API 也遵循同样原则：router 只调用 structured service，并把 Pydantic model 转成 dict 返回，不复制 search、evidence、prompt 或 LLM 逻辑。

### 4.7 Redis / Celery 异步任务

准备计划生成会调用 LLM，耗时和稳定性都不适合一直阻塞 HTTP 请求。所以我新增了 Celery 异步任务层：

- `POST /api/preparation/plan-tasks`：提交准备计划任务。
- `GET /api/tasks/{task_id}`：查询任务状态。
- Redis DB 0 默认作为 broker。
- Redis DB 1 默认作为 result backend。
- Celery worker 执行实际 preparation service。

同时我保留了同步接口 `POST /api/preparation/plan`，方便开发调试和小规模调用。

为了验证真实 Redis -> worker -> result backend 链路，我还新增了轻量 `system.ping` task。它不调用 LLM、不访问数据库，只用于本地集成验收。

## 5. 技术架构

```text
Streamlit UI
  ↓
Agent / Core
  ↓
Prompts
  ↓
Knowledge Base
  ↓
Preparation Service
  ↓
FastAPI API
  ↓
Celery Worker
  ↓
Redis Broker / Result Backend
```

模块职责：

```text
core/           转写解析、LLM 分析、基础存储
agent/          Orchestrator 与 Tool 链路
prompts/        Prompt 模板与 Prompt Builder
knowledge/      knowledge_chunks、检索、Evidence Context
preparation/    准备计划 service
api/            FastAPI router 与 Pydantic schema
worker/         Celery app 与异步任务
tests/          单元测试、API 测试、可选集成测试
scripts/        本地启动脚本
docs/           项目文档
```

## 6. 防幻觉设计

防幻觉是这个项目的核心亮点之一。我没有让模型直接自由生成建议，而是引入了“先检索证据，再基于证据生成”的约束。

具体设计包括：

- Evidence Context 中每条证据都有稳定编号 `[E1]`、`[E2]`。
- Prompt 要求所有历史表现判断必须引用证据编号。
- 如果证据不足，必须明确写“历史证据不足”。
- full-context 分析中区分能力不足、证据不足和覆盖缺口。
- 禁止把“建议补充展示”写成“候选人已经做到”。
- 空 evidence 时不允许生成具体历史表现判断，只能给通用准备计划。
- 测试中构造 golden case，检查 Prompt 是否包含未验证、N/A、证据不足、覆盖缺口等关键约束。

这个设计的价值是：模型可以给建议，但不能随意替候选人编造历史能力或项目经历。

## 7. 后端工程化设计

这个项目不仅是 Prompt Demo，也包含后端工程化拆分：

- FastAPI 提供服务化接口。
- Pydantic 做参数校验，非法输入由框架返回 422。
- preparation service 复用底层 search、context、prompt 和 LLM 调用，不把业务逻辑写在 router 里。
- Celery 解耦长耗时 LLM 任务，避免 HTTP 请求长时间阻塞。
- Redis 用作 broker 和 result backend。
- API 和 worker 通过环境变量共享 DB 路径和 Redis 配置。
- 单元测试 mock LLM、Celery 和 Redis，保证默认测试稳定。
- integration test 默认跳过，只有显式设置环境变量时才运行真实 Redis / Celery 链路。

## 8. 测试设计

### 8.1 单元测试

单元测试覆盖：

- Prompt builder。
- structured output schema / parser。
- knowledge repository。
- keyword / FTS search。
- evidence context builder。
- preparation service。
- worker task 普通函数。

### 8.2 API 测试

API 测试使用 FastAPI `TestClient`，覆盖：

- health check。
- knowledge search。
- evidence context。
- preparation plan。
- structured preparation plan。
- task submit。
- task status。

### 8.3 LLM 测试策略

默认测试不调用真实 LLM，而是通过 monkeypatch mock LLM 输出。

为了验证 Prompt 质量，我新增了人工评测样本和 expected JSON，重点检查模型输入是否能表达这些规则：

- 未验证能力不能强行扣分。
- 不能编造候选人没有展示过的历史能力。
- RAG 未完整实现时不能写成完整落地。
- 微调未落地时不能包装成项目经验。
- 后端工程能力没有被问到时应标记证据不足或未验证。

### 8.4 Celery / Redis 测试策略

默认 pytest 不依赖 Redis，也不启动 Celery worker。

Celery `delay` 和 `AsyncResult` 在单元测试中使用 monkeypatch；真实 Redis/Celery 只通过 `system.ping` 做本地可选集成验收。

只有设置下面的环境变量时，才会运行真实集成测试：

```bash
RUN_CELERY_INTEGRATION=1
```

## 9. API 设计简述

```text
GET  /api/health
POST /api/knowledge/search
POST /api/knowledge/evidence-context
POST /api/preparation/plan
POST /api/preparation/structured-plan
POST /api/preparation/plan-tasks
POST /api/tasks/ping
GET  /api/tasks/{task_id}
```

- `search`：检索历史知识库，返回 chunk 来源、snippet 和 score。
- `evidence-context`：返回 `[E1]` 格式证据上下文，不调用 LLM。
- `preparation/plan`：同步生成准备计划。
- `preparation/structured-plan`：同步生成结构化 JSON 准备计划。
- `preparation/plan-tasks`：异步提交准备计划任务。
- `tasks/{task_id}`：查询 Celery 任务状态和结果。
- `tasks/ping`：验证 Redis/Celery 链路。

## 10. 面试中可以强调的亮点

- 不是简单调用大模型，而是完整的大模型应用闭环。
- 有从面试转写 -> 分析 -> 知识库 -> 检索 -> 准备计划的链路。
- 有 evidence-based Prompt 设计，降低模型幻觉。
- 有“未验证能力不误判”的评价逻辑。
- 有 FastAPI 服务化能力。
- 有 Redis / Celery 异步任务化能力。
- 有结构化输出能力，便于前端展示、自动测试和后续持久化。
- 有完整测试策略，默认测试不依赖真实外部服务。
- 架构分层清晰，API / service / knowledge / worker 职责分离。
- 能同时体现大模型应用算法能力和 Python 后端工程能力。

## 11. 当前限制

- 当前检索主要是 keyword / FTS，还没有接 embedding retriever。
- 当前没有实现 rerank。
- 当前没有做模型微调。
- 当前 Structured Output 先支持 preparation plan，full-context analysis、summary 等仍主要是 Markdown。
- 当前 structured preparation plan 只有同步 API，尚未接入 Celery 异步任务。
- 当前异步任务结果主要依赖 Redis result backend，尚未持久化到 `task_records` 表。
- 当前 SQLite 更适合 MVP、本地开发和演示，生产环境可迁移 MySQL / PostgreSQL。
- 当前没有完整用户系统和权限控制。
- preparation task 调用真实 LLM 时依赖 API key、网络和代理。

## 12. 后续规划

1. 将 Structured Output 扩展到 full-context analysis、summary 和 scoring。
2. structured preparation plan 接入 Celery 异步任务。
3. `task_records` 持久化。
4. Docker Compose 编排 API / worker / Redis。
5. MySQL / PostgreSQL 替换 SQLite。
6. Embedding retriever + hybrid retrieval。
7. Rerank。
8. 更完整的 citations。
9. UI 接入异步任务状态。
10. Prompt evaluation golden cases 增强。
11. 面试准备计划长期追踪。

## 13. 面试回答模板

我做的 InterviewAce 是一个 AI 面试复盘与准备系统，最初是 Streamlit MVP，后来我把它逐步演进成了带知识库、证据检索、FastAPI 接口、Celery 异步任务和结构化输出的后端大模型应用。

核心流程是先解析面试转写，生成结构化复盘，再把复盘结果沉淀成 `knowledge_chunks`。后续准备面试时，系统会通过 keyword / FTS 检索历史知识库，构建 `[E1]`、`[E2]` 这样的 Evidence Context，再让模型基于这些历史证据生成下一次准备计划。准备计划既保留 Markdown 阅读版，也新增了 Pydantic schema 校验后的结构化 JSON 版本，方便前端展示、自动测试和后续持久化。

为了减少幻觉，我在 Prompt 里要求所有历史表现判断必须引用证据编号；如果证据不足，就明确写“历史证据不足”，不能把规划中的能力包装成已完成能力。工程上我用 FastAPI 暴露检索和准备计划接口，用 Celery/Redis 把 LLM 长任务异步化，并通过 mock LLM、mock Celery 和可选 Redis integration test 保证默认测试稳定。
