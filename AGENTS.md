# InterviewAce - AI 面试复盘驾驶舱

## 项目简介

InterviewAce 是一个基于 AI 的面试复盘与精进工具。用户上传通过**讯飞听见**导出的面试转写文件（`.txt`），系统自动解析对话结构，按话题生成结构化反馈报告，并将复盘结果沉淀为历史记录、题库和成长趋势。

**当前状态**：MVP 主链路已跑通，代码还包含历史复盘、话题分组、整体总结、五维评分、题库和成长追踪页面。

---

## 技术栈

- **语言**：Python 3.11+
- **前端**：Streamlit（第一版，快速验证）
- **转录方案**：讯飞听见（用户手动导出 .txt 文件上传，不调用 Whisper API）
- **AI 分析**：DeepSeek API（OpenAI SDK 兼容调用，当前模型见 `core/analyzer.py`）
- **存储**：SQLite（第一版）
- **环境管理**：python-dotenv
- **图表**：Plotly（成长追踪页面）

---

## 快速开始

```bash
source .venv/bin/activate
streamlit run app.py
python -m pytest tests/ -v
```

启动后访问 http://localhost:8501。

必需环境变量：

```bash
DEEPSEEK_API_KEY=...
```

`.env` 为本地私密配置，不提交 git；`.env.example` 维护必需变量名。

---

## 目录结构

```
interviewace/
├── AGENTS.md
├── .env                    # API Keys，不提交 git
├── .env.example
├── requirements.txt
├── app.py                  # Streamlit 入口
├── core/
│   ├── __init__.py
│   ├── parser.py           # 讯飞转写文件解析（替代 transcriber.py）
│   ├── analyzer.py         # AI 分析（DeepSeek，OpenAI SDK 兼容调用）
│   └── storage.py          # SQLite 读写
├── pages/
│   ├── question_bank.py    # Streamlit 题库页面
│   └── growth.py           # Streamlit 成长追踪页面
├── prompts/
│   └── interview_analysis.py   # Prompt 模板管理
├── tests/
│   ├── __init__.py
│   ├── test_analyzer.py    # analyzer 纯函数测试
│   ├── test_parser.py      # parser 单元测试
│   └── test_storage.py     # storage 单元测试
└── data/
    ├── .gitkeep
    └── interviews.db       # SQLite 数据库（运行时自动生成，不应提交）
```

---

## 转写文件规范：讯飞听见格式

讯飞听见导出的 .txt 文件格式如下，`parser.py` 需严格按照此格式解析：

```
标题行（第一行，如：AI技术在财务管理与面试中的应用）
说话人1 00:00
[说话人1的内容...]

说话人2 00:23
[说话人2的内容...]

说话人1 00:32
[说话人1的内容...]
```

### 解析规则
- **说话人识别**：`说话人1` 默认为候选人（我），`说话人2` 默认为面试官
- **时间戳格式**：`MM:SS` 或 `HH:MM:SS`，解析时保留备用
- **段落合并**：同一说话人连续多段文字合并为一个发言块
- **角色覆盖**：`parse_file()` 支持通过 `role_map` 覆盖说话人角色；当前 `app.py` 尚未提供 UI 切换入口
- **尾部过滤**：忽略「以上内容由AI生成，仅供参考」等系统附加行

### parser.py 输出数据结构
```python
@dataclass
class DialogueTurn:
    speaker: str          # "interviewer" 或 "candidate"
    timestamp: str        # 原始时间戳字符串
    content: str          # 发言内容

@dataclass
class InterviewSession:
    title: str                      # 文件标题（第一行）
    turns: list[DialogueTurn]       # 完整对话轮次
    candidate_turns: list[str]      # 仅候选人发言（用于分析）
```

---

## Prompt 与 AI 调用

`prompts/interview_analysis.py` 是产品核心，所有 Prompt 模板以源码为准。不要在文档中复制并维护第二份完整 Prompt，避免和真实调用逻辑漂移。

当前包含：
- `ANALYSIS_PROMPT_TEMPLATE`：单个话题/问答复盘
- `SUMMARY_PROMPT_TEMPLATE`：整体复盘总结
- `GROUPING_PROMPT_TEMPLATE`：问题话题分组，要求模型只输出 JSON
- `SCORING_PROMPT_TEMPLATE`：五维能力评分，要求模型只输出 JSON

`core/analyzer.py` 通过 `openai.OpenAI` 兼容客户端调用 DeepSeek：
- 模型常量：`_MODEL = "deepseek-chat"`
- API 地址：`_BASE_URL = "https://api.deepseek.com"`
- API Key：`DEEPSEEK_API_KEY`
- 单次超时：`_API_TIMEOUT = 60`

JSON 类输出必须做解析校验和降级：
- 话题分组失败时，`group_turns()` 降级为每轮单独分组
- 评分失败时，`score_session()` 返回 `None`，不阻断报告展示和保存
- Markdown fence 兼容逻辑在 `_strip_markdown_fence()`

### 分析维度设计依据
- 基于 **STAR 面试法**（Situation / Task / Action / Result）
- 评估维度参考真实 AI 面试产品的评分标准
- 输出结构围绕「知道哪错了 → 知道怎么改 → 知道怎么练」闭环设计

Prompt 里包含针对 AI 行业面试和语音识别误差的前置说明。修改 Prompt 输出结构时，必须同步检查 `core/analyzer.py` 的 `extract_questions()`，因为题库沉淀依赖「参考答案框架」「等级判定」等标题/段落。

---

## 第一版实现目标（MVP）

注意：下面是原始 MVP 范围，当前代码已经实现了部分后续能力（题库、成长追踪、历史记录、话题分组、整体总结、评分）。

### 功能范围
- [x] 设计分析 Prompt
- [x] 确定转录方案（讯飞听见手动导出）
- [x] 上传讯飞转写 .txt 文件
- [x] 解析文件，识别说话人角色（面试官 / 候选人）
- [ ] UI 支持手动确认说话人角色（`parse_file` 支持 `role_map`，但 `app.py` 尚未暴露 UI）
- [x] 用户输入岗位方向
- [x] 按问答/话题调用 DeepSeek API 完成分析
- [x] 展示结构化反馈报告
- [x] 将记录存入 SQLite
- [x] 历史复盘侧边栏与详情查看
- [x] 话题分组与整体复盘总结
- [x] 五维能力评分
- [x] 自动沉淀题目到题库
- [x] 成长追踪页面（至少 2 次带完整评分的记录才展示趋势）

## 第二版已完成功能

- [x] 话题合并
- [x] 历史记录
- [x] 成长追踪
- [x] 面试题库

## 第三版已完成功能
- [x] 并行化话题分析（ThreadPoolExecutor，5话题从~5分钟压缩到<2分钟）
- [x] 模拟面试模式（对话式，st.chat_message，mock_phase 状态机控制，按question去重抽题）

### 明确不在第一版范围内
- 音频文件直接上传 / 自动转录
- 用户系统 / 登录
- 部署上线

---

## 当前应用流程

`app.py` 是 Streamlit 主入口，启动时会调用 `init_db()` 自动建表/迁移，然后执行以下链路：

1. 侧边栏展示历史复盘，点击后进入只读详情模式。
2. 上传讯飞听见 `.txt` 文件，写入临时文件后调用 `parse_file()`。
3. 预览解析出的发言块，默认 `说话人1=candidate`，其他说话人均为 `interviewer`。
4. 输入岗位方向后开始分析。
5. 将面试官问题与后续候选人回答配对，候选人回答少于 20 字会被过滤。
6. 调用 `group_turns()` 做话题分组，把同话题的多轮问答合并后调用 `analyze_turn()`。
7. 调用 `analyze_summary()` 生成整体总结，调用 `score_session()` 生成 5 个维度评分。
8. 调用 `save_session()` 保存会话、话题、总结和评分。
9. 从反馈中提取参考答案框架，调用 `add_question()` 自动写入题库。

### 问答配对规则

`app.py` 中的配对逻辑是产品行为的一部分：
- 连续面试官发言会合并为一个问题
- 问题之后的下一个候选人发言作为回答，不要求严格紧邻
- 候选人回答长度少于 `_MIN_ANSWER_LEN = 20` 时跳过分析
- 分组后的多轮问答会合并成一个话题再分析

---

## 数据库约定

SQLite 默认路径为 `data/interviews.db`，由 `core/storage.py` 统一管理。

当前表结构：
- `sessions`：面试会话、岗位方向、创建时间、整体总结、五维评分字段
- `turns`：每个已分析话题/轮次的问题、回答、反馈、话题名
- `questions`：从历史复盘中沉淀出的题库题目、参考答案框架、难度、掌握程度

`init_db()` 内含向后兼容的 `ALTER TABLE` 逻辑。新增持久化字段时，应同步更新：
- `core/storage.py`
- `tests/test_storage.py`
- 本文件的数据库说明

测试必须使用临时数据库路径，不污染 `data/interviews.db`。

---

## 多页面约定

Streamlit 会自动识别 `pages/` 下的页面：

- `pages/question_bank.py`：按掌握程度浏览题库，支持更新 `mastery`
- `pages/growth.py`：读取完整评分历史，展示最近一次雷达图和多维趋势折线图

题库数据来自主流程的自动沉淀，当前不是手动录入题库。

---

## 测试覆盖

当前测试文件：
- `tests/test_parser.py`：讯飞听见格式、时间戳、角色覆盖、尾部过滤、空文件/缺失文件
- `tests/test_storage.py`：建表幂等、保存/查询会话、评分字段、题库 CRUD、成长历史
- `tests/test_analyzer.py`：JSON/fence 解析校验、评分校验、题目信息提取

涉及以下变更时必须补测试：
- 解析规则、说话人默认映射、尾部过滤
- SQLite 表结构、迁移、查询排序、持久化字段
- Prompt 输出格式对 `extract_questions()` 的影响
- JSON 输出校验或降级策略

---

## 代码约定

- 所有 API Key 通过 `.env` 注入，禁止硬编码
- 当前 API 环境变量为 `DEEPSEEK_API_KEY`，参考 `.env.example`
- `core/analyzer.py` 使用 `openai.OpenAI`，但 `base_url` 指向 DeepSeek；不要把它误改成 OpenAI 官方接口
- 函数必须有类型注解（Type Hints）
- 每个核心函数写简短 docstring 说明输入输出
- 错误处理：文件解析失败 / API 调用失败需捕获异常并在 UI 显示友好提示
- **不引入新依赖，除非先与人确认**
- 数据库操作统一在 `core/storage.py` 中，不在其他文件直接操作 DB
- LLM 要求 JSON 输出的功能必须做解析校验和降级，不要让 JSON 解析失败中断主流程
- 涉及 Prompt 输出结构的变更，要同步检查 `extract_questions()` 中基于标题/段落的提取逻辑
- Streamlit 页面负责交互与展示，业务规则优先沉到 `core/`，便于测试
- 新增页面放在 `pages/`，共享持久化能力从 `core.storage` 引入

## 常见修改触点

- 调整转写格式：改 `core/parser.py`，补 `tests/test_parser.py`
- 调整分析结构：改 `prompts/interview_analysis.py`，检查 `core/analyzer.py` 和 `tests/test_analyzer.py`
- 调整保存字段：改 `core/storage.py`、`tests/test_storage.py`、本文件数据库说明
- 调整上传/分析流程：改 `app.py`，留意历史查看模式和保存流程
- 调整题库：改 `pages/question_bank.py` 与 `core/storage.py`
- 调整成长追踪：改 `pages/growth.py` 与 `get_scores_history()`

## 已知限制与待办

- UI 尚未暴露说话人角色切换；`parse_file()` 已支持 `role_map`
- 主流程仍依赖外部 DeepSeek API，测试不应真实调用网络
- 暂无用户系统，所有数据写入本地 SQLite
- 暂无音频上传和自动转录能力，转录由讯飞听见完成
- 模拟面试题目来源依赖历史复盘沉淀，新用户题库为空时无法使用

## 禁止事项

- 不要自作主张更改 Prompt 模板结构
- 不要在没有确认的情况下切换 AI 模型
- 不要一次实现超出当前阶段目标的功能
- 不要引入 Whisper 或任何音频处理库（转录由用户在讯飞听见完成）
- 不要在页面中绕过 `core/storage.py` 直接访问 SQLite
