# InterviewAce · AI 面试复盘驾驶舱

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red)
![Tests](https://img.shields.io/badge/Tests-71%20passed-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green)

> 上传面试录音转写文件，AI 自动复盘、评分、沉淀题库、追踪成长。

---

## 项目背景

面试复盘效率提高插件：
本项目针对：不知道哪里答得不好、知道问题不知道怎么改、复盘了也容易忘。
InterviewAce 从自身痛点出发，构建了一套完整的 AI 驱动复盘工具。

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 📄 智能解析 | 解析讯飞听见转写文件，自动识别面试官与候选人 |
| 👥 角色确认 | 上传后可手动确认候选人说话人，其余说话人自动视为面试官 |
| 🧠 全量复盘 | 基于完整面试上下文生成结构化反馈，避免逐轮分析割裂语境 |
| 🗂️ 话题分组 | 保留话题分组分析链路，可将多轮对话按话题合并 |
| 🔍 STAR 复盘 | 基于 STAR 面试法生成结构化反馈报告 |
| 📋 整体总结 | 跨话题识别核心问题、亮点与优先改进建议 |
| 📊 五维评分 | STAR完整度、技术深度、表达逻辑、主动性、结果导向 |
| 📚 题库沉淀 | 自动将弱项话题沉淀为题库，支持掌握程度追踪 |
| 📈 成长追踪 | 跨多次面试的雷达图与折线趋势图 |
| 🎤 模拟面试 | 从题库抽题练习，并对回答生成即时反馈 |
| 🎯 练习计划 | 基于历史评分和题库弱项生成维度强化计划 |
| 🗄️ 历史回顾 | 侧边栏随时查看历史复盘报告 |

---

## 技术架构

```
用户上传转写文件
        ↓
  Agent Orchestrator
        ↓
┌──────────────────────────────────────┐
│  Tool 1: parse_interview             │  讯飞格式解析，说话人分离
│  Tool 2: analyze_full_interview      │  完整上下文复盘（默认链路）
│  Tool 3: generate_summary            │  跨话题整体总结
│  Tool 4: score_performance           │  五维能力评分（JSON 输出）
│  Tool 5: save_results                │  SQLite 持久化 + 题库沉淀
└──────────────────────────────────────┘
        ↓
  Streamlit UI（主页 + 题库 + 成长追踪 + 模拟面试 + 练习计划）
```

每个 Tool 返回统一的 `ToolResult(success, data, error)`。Orchestrator 默认走完整上下文复盘链路，同时保留 `topic` 模式：话题分组失败时可降级为逐轮分析，评分或总结失败时不阻断主流程。

---

## 目录结构

```
interviewace/
├── app.py                  # Streamlit 主入口：上传、预览、分析、历史查看
├── agent/
│   ├── orchestrator.py     # 主控 Agent，管理分析链路与降级策略
│   ├── tools.py            # Tool 封装层（ToolResult 标准返回）
│   └── schemas.py          # ToolResult / AgentContext / Intent 数据结构
├── core/
│   ├── parser.py           # 讯飞转写格式解析
│   ├── analyzer.py         # DeepSeek API 调用（含 JSON 校验与降级）
│   └── storage.py          # SQLite 读写（sessions / turns / questions）
├── prompts/
│   └── interview_analysis.py  # 分析、总结、分组、评分、模拟面试、练习计划 Prompt
├── pages/
│   ├── question_bank.py    # 题库页面
│   ├── growth.py           # 成长追踪页面
│   ├── mock_interview.py   # 模拟面试页面
│   └── practice_plan.py    # 练习计划页面
├── data/
│   └── interviews.db       # 本地 SQLite 数据库（运行时生成/更新）
└── tests/                  # 71 个单元测试
    ├── test_parser.py
    ├── test_storage.py
    ├── test_analyzer.py
    └── test_orchestrator.py
```

---

## 🌐 在线体验
> 🔗 [点击访问 InterviewAce](https://interviewace-6qdx2saopbqkyz7hqq4hjg.streamlit.app/)
>
> 无需安装，上传讯飞听见转写文件即可开始使用。

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

**1. 完整上下文优先**
面试中的同一能力点可能散落在多轮对话中，默认链路会先构建完整问答上下文，再生成整体复盘，减少逐轮分析导致的语境割裂。

**2. 分层降级策略**
话题分组失败 → 降级为逐轮分析；评分失败 → 跳过不阻断主流程；
分析失败 → 自动重试一次。核心链路在 API 不稳定时仍能跑通。

**3. Prompt 针对语音识别噪音优化**
面试录音转写存在大量同音字错误（如「癌症者」=「Agent」），
Prompt 前置说明要求 AI 自动修正理解，不将识别错误归咎于候选人。

**4. Tool 层标准化**
所有 AI 调用和数据库操作封装为统一 ToolResult，
Orchestrator 通过声明式工具链驱动，便于扩展新意图和新工具。

**5. 复盘到练习的闭环**
复盘报告会沉淀题库，题库掌握程度、模拟面试反馈和历史评分共同支撑成长追踪与练习计划。

---

## 测试覆盖

```
71 个单元测试，覆盖：
- 转写格式解析（讯飞听见格式、时间戳、说话人映射、尾部过滤）
- SQLite CRUD（会话、话题、评分、题库）
- Analyzer 纯逻辑（JSON 校验、降级、题目提取、模拟面试评分）
- Agent 层（ToolResult、AgentContext、工具链、降级路径）
```

---

## 后续规划

- [ ] 实时录音转写接入，降低使用门槛
- [ ] 支持更多转写文件格式
- [ ] 为模拟面试增加多轮追问能力
- [ ] 增加导出复盘报告功能

---

## 📸 功能截图
> 截图待补充
