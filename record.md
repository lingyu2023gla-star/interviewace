# InterviewAce · 项目记录文档

> 用于跨对话端口延续项目规划，记录背景、已完成实现、遇到的问题与下一步方向。

---

## 一、个人背景与项目动机

**作者情况：**
- 不满30岁，AI 行业从业者，代码开发经验尚浅
- 曾在牛客做 AI 面试相关产品（使用 STAR 面试法评分，熟悉面试评测体系）
- 因公司架构调整离职，当前处于求职阶段
- 有一位同龄朋友（女朋友发小）在 AI 初创公司担任类 CTO 职位，已有深度交流

**项目起因：**
- 朋友建议做「AI 面试驾驶舱」来辅助面试复盘与精进
- 自身痛点：不知道哪里答得不好 / 知道问题不知道怎么改 / 复盘了也忘
- 定位：A（自用）→ C（简历项目）→ B（产品潜力）

**技术偏好：**
- 主语言 Python
- 使用 Claude Code（CC）执行代码，本人负责决策判断
- AI 推理模型：DeepSeek API（`deepseek-chat`，兼容 OpenAI SDK）
- 转录方案：讯飞听见手动导出 `.txt`（已有真实样本：`tests/fixtures/sample_interview.txt`）

---

## 二、项目基本信息

| 项目 | 信息 |
|------|------|
| 项目名 | InterviewAce |
| 本地路径 | `/Users/apple/workspace/yuling/interviewace` |
| 启动命令 | `source .venv/bin/activate && streamlit run app.py` |
| 测试命令 | `.venv/bin/python -m pytest tests/ -v` |
| Python 版本 | 3.14.0（已用 .venv 隔离） |
| 数据库 | SQLite，路径 `data/interviews.db` |
| 环境变量 | `DEEPSEEK_API_KEY`（在 `.env` 中） |

---

## 三、已完成的完整实现

### 3.1 目录结构

```
interviewace/
├── CLAUDE.md               # CC 项目说明书（已更新到 Agent 架构）
├── README.md               # 对外展示文档（已生成）
├── app.py                  # Streamlit 主入口（已切换到 Agent 链路）
├── agent/
│   ├── __init__.py
│   ├── schemas.py          # ToolResult / AgentContext / Intent
│   ├── tools.py            # 6个 Tool 封装（ToolResult 标准返回）
│   └── orchestrator.py     # 主控 Agent，声明式工具链+降级策略
├── core/
│   ├── __init__.py
│   ├── parser.py           # 讯飞转写解析（含 parse_text()）
│   ├── analyzer.py         # DeepSeek 调用（含超时、JSON校验、降级）
│   └── storage.py          # SQLite（sessions/turns/questions 三表）
├── prompts/
│   └── interview_analysis.py  # 4套 Prompt 模板
├── pages/
│   ├── question_bank.py    # 题库页面（三 tab）
│   └── growth.py           # 成长追踪（雷达图+折线图，plotly）
├── tests/
│   ├── test_parser.py      # 9个测试
│   ├── test_storage.py     # 20个测试
│   ├── test_analyzer.py    # 23个测试
│   └── test_orchestrator.py # 14个测试
└── data/
    └── interviews.db       # 运行时自动生成
```

**测试总数：66个，全部通过，耗时约 1s**

---

### 3.2 核心功能清单

| 功能 | 状态 | 说明 |
|------|------|------|
| 讯飞转写文件解析 | ✅ | 说话人分离、时间戳、尾部过滤 |
| AI 话题分组 | ✅ | DeepSeek JSON输出，失败降级为逐轮 |
| STAR 结构复盘 | ✅ | 逐话题分析，含参考答案框架 |
| 整体复盘总结 | ✅ | 跨话题，指向具体话题名 |
| 五维能力评分 | ✅ | STAR完整度/技术深度/表达逻辑/主动性/结果导向 |
| 历史记录查看 | ✅ | 侧边栏，点击回看完整报告 |
| 题库自动沉淀 | ✅ | 从分析文本提取参考答案+难度 |
| 掌握程度追踪 | ✅ | new/learning/mastered 三态 |
| 成长追踪可视化 | ✅ | 雷达图（当次）+折线图（趋势） |
| Agent 架构 | ✅ | Orchestrator + 6个 Tool + ToolResult |
| UI 说话人角色切换 | ✅ | role_map 传入 orchestrator |
| 结构化 JSON 输出 | ✅ | analyze_turn / analyze_mock_answer |
| 流式总结展示 | ✅ | analyze_summary_stream |
| 模拟面试模式 | ✅ | 对话式，mock_phase 状态机 |
| 练习计划生成 | ✅ | 维度强化，pages/practice_plan.py |
| 并行化话题分析 | ✅ | ThreadPoolExecutor |
| 单元测试覆盖 | ✅ | 66个，覆盖纯逻辑层 |

---

### 3.3 Agent 架构设计

```
用户输入
    ↓
Streamlit UI（app.py）
    ↓
InterviewOrchestrator.run_analyze_interview()
    ↓ 声明式工具链（6步）
Tool 1: tool_parse_interview     → 解析转写文本，输出 turns + pairs
Tool 2: tool_group_topics        → AI话题分组（temperature=0），失败→每轮独立
Tool 3: tool_analyze_topics      → 逐话题 STAR 复盘，失败→重试一次
Tool 4: tool_generate_summary    → 整体总结，失败→跳过
Tool 5: tool_score_performance   → 五维评分（temperature=0），失败→跳过
Tool 6: tool_save_results        → SQLite存储+题库沉淀
    ↓
ToolResult(success, data, error) 统一返回
```

**降级策略表：**
```python
FALLBACK_STRATEGIES = {
    "group_topics":      "every_turn_standalone",
    "score_performance": "skip",
    "generate_summary":  "skip",
    "analyze_topics":    "retry_once",
}
```

**on_step 回调**：每步完成后通知 UI 更新进度条，Orchestrator 不依赖 Streamlit，可独立运行。

---

### 3.4 数据库表结构

```sql
-- 面试会话
sessions (id, title, job_direction, created_at, summary,
          score_star_completeness, score_technical_depth,
          score_logical_clarity, score_proactiveness, score_result_orientation)

-- 话题分析结果
turns (id, session_id, turn_index, topic, question, answer, feedback)

-- 题库
questions (id, source_session_id, topic, question, reference_answer,
           difficulty, mastery, created_at)
```

---

### 3.5 Prompt 体系

| Prompt | 用途 | 关键设计 |
|--------|------|---------|
| ANALYSIS_PROMPT | 单话题 STAR 复盘 | 前置说明：AI行业+语音识别噪音处理+忽略口语 |
| SUMMARY_PROMPT | 整体总结 | 输入各话题反馈摘要（600字），输出指向话题名 |
| GROUPING_PROMPT | 话题分组 | 只输出 JSON，temperature=0 |
| SCORING_PROMPT | 五维评分 | 只输出 JSON，每维含score+reason |

**关键 Prompt 优化记录：**
- 加入前置说明：语音识别错误（如「癌症者」=「Agent」）不得归咎候选人
- 总结中「出现位置」改为话题名而非轮次编号
- `extract_questions()` 依赖「参考答案框架」和「等级判定」标题，Prompt 结构变更需同步检查

---

## 四、遇到的问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| API 无限卡住 | 无超时设置 | `_API_TIMEOUT = 60`，三层异常捕获 |
| openai SDK proxies 报错 | httpx 版本不兼容 | 固定 `openai==1.30.1 httpx==0.27.0` |
| `socks5h` 代理报错（CC环境） | CC 系统代理不兼容 | 手动运行正常，CC环境跳过（不影响使用） |
| 总结引用轮次编号而非话题 | summary prompt 输入未感知「组」 | 修改 rounds_lines 标题为话题名 |
| AI 把语音识别错误归咎候选人 | Prompt 无前置约束 | 加入前置说明+强约束「不得出现在报告中」 |
| SQLite 排序不稳定 | 时间戳精度只到秒 | 加 `id DESC` 次级排序 |
| tool_analyze_topics 参数混淆 | turns 和 pairs 语义不清 | 重命名参数为 `pairs`，删除 `_normalize_pair` |
| 雷达图渲染成饼状图 | plotly 参数配置错误 | 改用 `go.Scatterpolar` 正确写法 |

---

## 五、已验证的真实数据

- 使用过的真实面试转写文件：`AI技术在财务管理与面试中的应用`（讯飞听见格式）
- 已跑通完整链路多次，分析质量验证通过
- 五维评分示例（一次真实输出）：
  - STAR完整度：5/10
  - 技术深度：7/10
  - 表达逻辑：5/10
  - 主动性：4/10
  - 结果导向：5/10

---

## 六、下一步规划（优先级排序）

### 高优先级
- [x] ~~**并行化 API 调用**：已用 `ThreadPoolExecutor` 并行化 `tool_analyze_topics`~~
- [x] ~~**流式输出**：已实现 `analyze_summary_stream`，总结展示支持打字机效果~~
- [x] ~~**模拟面试模式**：已实现对话式页面、`mock_phase` 状态机和去重抽题~~
- [x] ~~**练习计划生成**：已实现维度强化计划页面 `pages/practice_plan.py`~~
- [x] ~~**UI 说话人角色切换**：`role_map` 已传入 orchestrator，预览区支持互换角色~~
- [x] ~~**record.md 同步更新**~~
- [ ] **部署上线**：用户系统、云端数据库、公网访问

### 中优先级
- [ ] **扩展 Agent 意图**：当前只实现了 `ANALYZE_INTERVIEW`，下一个建议实现 `PLAN_PREPARATION`（根据历史弱点和目标岗位生成练习计划）
- [ ] **UI 暴露说话人角色切换**：`parse_file()` 已支持 `role_map`，但 app.py 尚未提供切换入口

### 低优先级
- [ ] **实时录音转写接入**：降低使用门槛，当前依赖讯飞听见手动导出
- [ ] **模拟面试模式**：Agent 扮演面试官，针对历史弱点出题
- [ ] **部署上线**：用户系统、登录、云端部署

---

## 七、项目讲解要点（面试用）

### 30秒版本
「我做了一个 AI 面试复盘工具 InterviewAce。背景是自己有 AI 面试产品经验，离职后发现复盘效率低——不知道哪里答得不好，知道问题不知道怎么改。用 DeepSeek API 做了完整链路：上传讯飞转写文件，AI 按话题分组、STAR 复盘、五维评分，结果沉淀题库和成长趋势图。底层用 Agent 架构，声明式工具链驱动，66个单元测试。」

### 关键设计决策（面试展开点）
1. **话题合并**：同一话题跨多轮，先 AI 分组再整体分析，避免上下文割裂
2. **Prompt 噪音处理**：语音识别错误（「癌症者」=「Agent」）前置说明约束
3. **ToolResult 模式**：统一返回结构，错误处理变数据流而非异常控制流
4. **on_step 回调**：控制反转，Orchestrator 不依赖 Streamlit，可独立运行
5. **降级策略声明式**：每个 Tool 的容错行为集中管理，一眼看清全局容错逻辑

### 主动承认的技术债
- 多话题分析串行，应早期做并行化
- 题库参考答案依赖正则提取，Prompt 格式变更会影响提取结果（应改为结构化 JSON 输出）

---

## 八、技术栈总览

| 层次 | 技术 |
|------|------|
| 语言 | Python 3.14 |
| UI | Streamlit |
| AI 推理 | DeepSeek API（`deepseek-chat`，OpenAI SDK 兼容） |
| 转录 | 讯飞听见（手动导出 .txt） |
| 存储 | SQLite（via `core/storage.py`） |
| 图表 | Plotly（雷达图+折线图） |
| 测试 | pytest（66个，纯逻辑层，不 mock API） |
| 开发方式 | Claude Code 执行 + 人工决策 |

---

## 当前页面导航

- `app.py`：主入口，面试复盘
- `pages/question_bank.py`：题库
- `pages/growth.py`：成长追踪
- `pages/mock_interview.py`：模拟面试
- `pages/practice_plan.py`：练习计划

---

*最后更新：基于完整对话记录生成，涵盖从项目立项到 Agent 架构实现的全过程。*
