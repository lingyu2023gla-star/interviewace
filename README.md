# InterviewAce · AI 面试复盘驾驶舱

> 上传面试录音转写文件，AI 自动复盘、评分、沉淀题库、追踪成长。

---

## 项目背景

作者有 AI 面试产品的行业背景，离职后发现面试复盘效率极低：
不知道哪里答得不好、知道问题不知道怎么改、复盘了也容易忘。
InterviewAce 从自身痛点出发，构建了一套完整的 AI 驱动复盘工具。

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 📄 智能解析 | 解析讯飞听见转写文件，自动识别面试官与候选人 |
| 🗂️ 话题分组 | AI 自动将多轮对话按话题合并，避免上下文割裂 |
| 🔍 STAR 复盘 | 基于 STAR 面试法，逐话题生成结构化反馈报告 |
| 📋 整体总结 | 跨话题识别核心问题、亮点与优先改进建议 |
| 📊 五维评分 | STAR完整度、技术深度、表达逻辑、主动性、结果导向 |
| 📚 题库沉淀 | 自动将弱项话题沉淀为题库，支持掌握程度追踪 |
| 📈 成长追踪 | 跨多次面试的雷达图与折线趋势图 |
| 🗄️ 历史回顾 | 侧边栏随时查看历史复盘报告 |

---

## 技术架构

```
用户上传转写文件
        ↓
  Agent Orchestrator
        ↓
┌───────────────────────────────────┐
│  Tool 1: parse_interview          │  讯飞格式解析，说话人分离
│  Tool 2: group_topics             │  DeepSeek 话题分组（temperature=0）
│  Tool 3: analyze_topics           │  STAR 复盘，逐话题并发分析
│  Tool 4: generate_summary         │  跨话题整体总结
│  Tool 5: score_performance        │  五维能力评分（JSON 输出）
│  Tool 6: save_results             │  SQLite 持久化 + 题库沉淀
└───────────────────────────────────┘
        ↓
  Streamlit UI（主页 + 题库 + 成长追踪）
```

每个 Tool 返回统一的 `ToolResult(success, data, error)`，Orchestrator 按声明式降级策略处理失败。

---

## 目录结构

```
interviewace/
├── app.py                  # Streamlit 主入口
├── agent/
│   ├── orchestrator.py     # 主控 Agent，管理工具链与降级策略
│   ├── tools.py            # Tool 封装层（ToolResult 标准返回）
│   └── schemas.py          # ToolResult / AgentContext / Intent 数据结构
├── core/
│   ├── parser.py           # 讯飞转写格式解析
│   ├── analyzer.py         # DeepSeek API 调用（含 JSON 校验与降级）
│   └── storage.py          # SQLite 读写（sessions / turns / questions）
├── prompts/
│   └── interview_analysis.py  # 4 套 Prompt 模板
├── pages/
│   ├── question_bank.py    # 题库页面
│   └── growth.py           # 成长追踪页面
└── tests/                  # 62 个单元测试
    ├── test_parser.py
    ├── test_storage.py
    ├── test_analyzer.py
    └── test_orchestrator.py
```

---

## 快速启动

```bash
git clone https://github.com/yourname/interviewace
cd interviewace
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填入 DEEPSEEK_API_KEY
streamlit run app.py
```

---

## 设计亮点

**1. 话题合并而非逐轮分析**
同一话题（如「离职原因」）可能跨多轮讨论，逐轮分析会割裂上下文。
系统先用 AI 对问题分组，再按话题合并后整体分析，反馈质量显著提升。

**2. 分层降级策略**
话题分组失败 → 降级为逐轮分析；评分失败 → 跳过不阻断主流程；
分析失败 → 自动重试一次。核心链路在 API 不稳定时仍能跑通。

**3. Prompt 针对语音识别噪音优化**
面试录音转写存在大量同音字错误（如「癌症者」=「Agent」），
Prompt 前置说明要求 AI 自动修正理解，不将识别错误归咎于候选人。

**4. Tool 层标准化**
所有 AI 调用和数据库操作封装为统一 ToolResult，
Orchestrator 通过声明式工具链驱动，便于扩展新意图和新工具。

---

## 测试覆盖

```
62 个单元测试，覆盖：
- 转写格式解析（讯飞听见格式、时间戳、说话人映射、尾部过滤）
- SQLite CRUD（会话、话题、评分、题库）
- Analyzer 纯逻辑（JSON 校验、降级、题目提取）
- Agent 层（ToolResult、AgentContext、工具链、降级路径）
```

---

## 后续规划

- [ ] 并行化 Tool 调用，缩短多话题分析时间
- [ ] 实时录音转写接入，降低使用门槛
- [ ] 模拟面试模式：Agent 扮演面试官，针对历史弱点出题
