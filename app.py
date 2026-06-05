"""
app.py — InterviewAce Streamlit 入口

链路：上传转写文件 → 解析预览 → 输入岗位方向 → 逐轮 AI 分析 → 展示报告
暂不接入 storage.py，后续迭代再加。
"""

import re

import streamlit as st

from core.parser import InterviewSession, parse_file
from core.storage import init_db, list_sessions, get_session, get_scores_history
from core.analyzer import analyze_summary_stream
from agent.orchestrator import orchestrator
from agent.schemas import ToolResult

# 候选人回答字数低于此阈值视为无实质内容，跳过分析
_MIN_ANSWER_LEN = 20

st.set_page_config(page_title="InterviewAce", page_icon="🎯", layout="centered")
init_db()
st.title("InterviewAce · 面试复盘助手")

# ── 侧边栏：历史复盘 ───────────────────────────────────────────────────────────

with st.sidebar:
    st.header("📚 历史复盘")
    sessions = list_sessions()
    if not sessions:
        st.caption("暂无历史记录")
    else:
        for s in sessions:
            label = f"{s['title'][:12]}… | {s['job_direction']} | {s['created_at'][:10]}"
            if st.button(label, key=f"session_{s['id']}"):
                st.session_state["viewing_session_id"] = s["id"]

# ── 历史记录查看模式 ───────────────────────────────────────────────────────────

if "viewing_session_id" in st.session_state:
    session_id = st.session_state["viewing_session_id"]
    record = get_session(session_id)
    if record:
        st.subheader(f"📄 {record['title']}")
        st.caption(f"岗位方向：{record['job_direction']} ｜ 时间：{record['created_at'][:10]}")

        if record.get("summary"):
            with st.container():
                st.subheader("📋 整体复盘总结")
                st.markdown(record["summary"])
                st.divider()

        st.subheader("📊 分析报告")
        for i, turn in enumerate(record["turns"]):
            topic = turn.get("topic", "")
            label = f"「{topic}」" if topic else f"第 {turn['turn_index']} 轮"
            with st.expander(label, expanded=(i == 0)):
                st.markdown("**面试问题**")
                st.info(turn["question"])
                st.markdown("**候选人回答**")
                st.info(turn["answer"])
                st.markdown("**AI 复盘反馈**")
                st.markdown(turn["feedback"])

        if st.button("← 返回上传新文件"):
            del st.session_state["viewing_session_id"]
            st.rerun()
        st.stop()


# ── Step 1: 上传文件 ───────────────────────────────────────────────────────────

uploaded = st.file_uploader("上传讯飞听见导出的转写文件（.txt）", type=["txt"])

if not uploaded:
    st.info("请上传转写文件以开始分析。")
    st.stop()

# 解析文件
try:
    import tempfile, os
    uploaded_bytes = uploaded.getvalue()
    uploaded_text = uploaded_bytes.decode("utf-8")
    speaker_labels = sorted(
        set(re.findall(r"^(说话人\d+)\s+\d{1,2}:\d{2}(?::\d{2})?", uploaded_text, re.M)),
        key=lambda label: int(re.search(r"\d+", label).group()),
    )
    if not speaker_labels:
        speaker_labels = ["说话人1", "说话人2"]

    file_key = f"{uploaded.name}_{uploaded.size}"
    if st.session_state.get("last_file_key") != file_key:
        st.session_state.last_file_key = file_key
        st.session_state.role_map = {
            label: "candidate" if label == speaker_labels[0] else "interviewer"
            for label in speaker_labels
        }
        if "candidate_speaker_select" in st.session_state:
            del st.session_state["candidate_speaker_select"]

    if "role_map" not in st.session_state:
        st.session_state.role_map = {
            label: "candidate" if label == speaker_labels[0] else "interviewer"
            for label in speaker_labels
        }

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(uploaded_bytes)
        tmp_path = tmp.name

    session_data: InterviewSession = parse_file(
        tmp_path,
        role_map=st.session_state.get("role_map"),
    )
    session = session_data
finally:
    try:
        os.unlink(tmp_path)
    except Exception:
        pass

if not session.turns:
    st.error("未能从文件中解析出任何对话轮次，请确认文件格式符合讯飞听见导出规范。")
    st.stop()


# ── Step 2: 对话预览 ───────────────────────────────────────────────────────────

st.subheader(f"📄 {session.title}")

candidate_count = sum(1 for t in session.turns if t.speaker == "candidate")
interviewer_count = sum(1 for t in session.turns if t.speaker == "interviewer")
preview_title = f"对话轮次预览 · 共 {len(session.turns)} 个发言块 · 候选人 {candidate_count} 轮 · 面试官 {interviewer_count} 轮"

with st.expander(preview_title, expanded=False):
    role_label = {"candidate": "👤 候选人", "interviewer": "🎙️ 面试官"}
    st.markdown("**说话人角色确认**")
    st.caption("请选择候选人；其余说话人将自动识别为面试官。")

    current_candidate = next(
        (label for label in speaker_labels if st.session_state.role_map.get(label) == "candidate"),
        speaker_labels[0],
    )
    selected_candidate = st.selectbox(
        "候选人说话人",
        speaker_labels,
        index=speaker_labels.index(current_candidate),
        key="candidate_speaker_select",
    )
    if selected_candidate != current_candidate:
        st.session_state.role_map = {
            label: "candidate" if label == selected_candidate else "interviewer"
            for label in speaker_labels
        }
        st.rerun()

    for i, turn in enumerate(session.turns):
        preview = turn.content[:30].replace("\n", " ")
        if len(turn.content) > 30:
            preview += "…"
        st.markdown(f"`{i+1}` **{role_label.get(turn.speaker, turn.speaker)}** `{turn.timestamp}` — {preview}")


# ── Step 3: 岗位方向输入 ───────────────────────────────────────────────────────

job_direction = st.text_input("岗位方向", placeholder="如：AI应用开发、产品经理、数据分析师")

if not job_direction.strip():
    st.warning("请输入岗位方向后再开始分析。")
    st.stop()


# ── Step 4: 开始分析按钮 ───────────────────────────────────────────────────────

if not st.button("🚀 开始分析", type="primary"):
    st.stop()


# ── Agent 分析链路 ────────────────────────────────────────────────────────────

# on_step 回调：每步完成后更新进度
step_labels = {
    "parse_interview": "解析转写文件…",
    "group_topics": "识别话题分组…",
    "analyze_topics": "逐话题分析…",
    "generate_summary": "生成整体总结…",
    "score_performance": "生成能力评分…",
    "save_results": "保存复盘记录…",
}
progress_bar = st.progress(0.0)
step_keys = list(step_labels.keys())
step_container = st.empty()

completed_steps: list[str] = []


def on_step(step_name: str, result: ToolResult) -> None:
    completed_steps.append(step_name)
    progress = len(completed_steps) / len(step_keys)
    progress_bar.progress(progress)
    step_container.caption(f"✅ {step_labels.get(step_name, step_name)}")


summary_container = st.container()

final_result = orchestrator.run_analyze_interview(
    text=uploaded_text,
    job_direction=job_direction.strip(),
    title=session_data.title,
    on_step=on_step,
    role_map=st.session_state.get("role_map"),
)

if not final_result.success:
    st.error(f"分析失败：{final_result.error}")
    st.stop()

data = final_result.data
feedbacks = data["feedbacks"]
summary = data["summary"]
scores = data["scores"]
session_id = data["session_id"]
questions_saved = data["questions_saved"]

st.success("分析完成！")
if questions_saved > 0:
    st.toast(f"📚 已沉淀 {questions_saved} 道题目到题库")
if scores is not None:
    st.toast("✅ 本次复盘已保存")
    with st.sidebar:
        st.divider()
        st.subheader("📊 本次评分")
        dim_labels = {
            "star_completeness": "STAR完整度",
            "technical_depth": "技术深度",
            "logical_clarity": "表达逻辑",
            "proactiveness": "主动性",
            "result_orientation": "结果导向",
        }
        for key, label in dim_labels.items():
            item = scores[key]
            st.metric(label, f"{item['score']}/10")
            st.caption(item["reason"])

st.divider()
st.subheader("📊 分析报告")

for idx, item in enumerate(feedbacks):
    topic = item.get("topic", "")
    turn_indices_str = str(item.get("index", idx + 1))
    label = f"「{topic}」" if topic else f"第 {idx+1} 轮"
    with st.expander(label, expanded=(idx == 0)):
        st.markdown("**面试问题**")
        st.info(item["question"])
        st.markdown("**候选人回答**")
        st.info(item["answer"])
        st.markdown("**AI 复盘反馈**")
        if item["feedback"].startswith("["):
            st.error(item["feedback"])
        else:
            st.markdown(item["feedback"])

with summary_container:
    st.subheader("📋 整体复盘总结")
    if summary:
        # 用流式重新展示总结（数据已存库，这里只做展示）
        with st.spinner("正在生成整体复盘总结…"):
            summary_placeholder = st.empty()
            streamed_text = ""
            for chunk in analyze_summary_stream(
                pairs_with_feedback=data["feedbacks"],
                job_direction=job_direction.strip(),
            ):
                streamed_text += chunk
                summary_placeholder.markdown(streamed_text + "▌")
            summary_placeholder.markdown(streamed_text)
    else:
        st.caption("总结生成失败，不影响查看分析报告")
    st.divider()
