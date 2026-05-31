import streamlit as st
from core.storage import list_questions, update_mastery
from core.analyzer import analyze_mock_answer, extract_mock_rating

st.set_page_config(page_title="模拟面试 · InterviewAce", page_icon="🎤", layout="centered")
st.title("🎤 模拟面试")

# ── 常量 ──────────────────────────────────────────────────────────────────────

RATING_TO_MASTERY = {
    "优秀": "mastered",
    "良好": "learning",
    "一般": "learning",
    "待改进": "new",
}

MASTERY_FILTER_OPTIONS = {
    "只练未掌握": "new",
    "练习中": "learning",
    "全部题目": None,
}

# ── Session State 初始化 ──────────────────────────────────────────────────────

if "mock_started" not in st.session_state:
    st.session_state.mock_started = False
if "mock_questions" not in st.session_state:
    st.session_state.mock_questions = []
if "mock_current_idx" not in st.session_state:
    st.session_state.mock_current_idx = 0
if "mock_chat_history" not in st.session_state:
    st.session_state.mock_chat_history = []
if "mock_job_direction" not in st.session_state:
    st.session_state.mock_job_direction = ""
if "mock_waiting_answer" not in st.session_state:
    st.session_state.mock_waiting_answer = False
if "mock_phase" not in st.session_state:
    st.session_state.mock_phase = "questioning"

# ── 开始界面 ──────────────────────────────────────────────────────────────────

if not st.session_state.mock_started:
    st.markdown("从题库中取题，AI 逐题出题并实时反馈。")

    job_direction = st.text_input(
        "岗位方向",
        placeholder="如：AI应用开发、产品经理",
        value=st.session_state.mock_job_direction,
    )

    filter_label = st.selectbox("练习范围", list(MASTERY_FILTER_OPTIONS.keys()))
    mastery_filter = MASTERY_FILTER_OPTIONS[filter_label]

    topic_questions = list_questions(mastery=mastery_filter)
    seen = {}
    for q in topic_questions:
        key = q["question"].strip()
        if key not in seen or q["id"] > seen[key]["id"]:
            seen[key] = q
    unique_count = len(seen)
    st.caption(f"当前范围共 {unique_count} 道题目（已去重）")

    max_q = st.slider("本次练习题数", min_value=1, max_value=min(10, max(1, len(topic_questions))), value=min(3, len(topic_questions)))

    if st.button("🚀 开始模拟面试", type="primary", disabled=not job_direction.strip() or len(topic_questions) == 0):
        import random
        # 按 question 内容去重，保留 id 最大的一条
        seen_questions: dict[str, dict] = {}
        for q in topic_questions:
            key = q["question"].strip()
            if key not in seen_questions or q["id"] > seen_questions[key]["id"]:
                seen_questions[key] = q
        unique_questions = list(seen_questions.values())
        selected = random.sample(unique_questions, min(max_q, len(unique_questions)))
        st.session_state.mock_questions = selected
        st.session_state.mock_current_idx = 0
        st.session_state.mock_chat_history = []
        st.session_state.mock_job_direction = job_direction.strip()
        st.session_state.mock_started = True
        st.session_state.mock_waiting_answer = True
        st.session_state.mock_phase = "questioning"
        st.rerun()

    if len(topic_questions) == 0:
        st.warning("当前范围没有题目，请先完成至少一次面试复盘以沉淀题库。")
    st.stop()

# ── 面试进行中 ────────────────────────────────────────────────────────────────

questions = st.session_state.mock_questions
current_idx = st.session_state.mock_current_idx
total = len(questions)

# 进度
st.progress((current_idx) / total)
st.caption(f"第 {min(current_idx + 1, total)} / {total} 题 · 岗位：{st.session_state.mock_job_direction}")

if current_idx < total:
    # 出当前题目：只在进入 questioning 阶段时追加一次。
    current_q = questions[current_idx]
    question_text = f"**第 {current_idx + 1} 题**\n\n{current_q['question']}"
    last_msg = st.session_state.mock_chat_history[-1] if st.session_state.mock_chat_history else None
    should_ask_question = (
        st.session_state.mock_phase == "questioning"
        and (last_msg is None or last_msg.get("kind") in {"feedback", "feedback_error"})
    )
    if should_ask_question:
        st.session_state.mock_chat_history.append({
            "role": "assistant",
            "content": question_text,
            "kind": "question",
            "question_idx": current_idx,
        })

# 渲染历史对话
for msg in st.session_state.mock_chat_history:
    with st.chat_message(msg["role"]):
        if msg.get("kind") == "feedback_error":
            st.error(msg["content"])
        else:
            st.markdown(msg["content"])

# 面试结束
if current_idx >= total:
    with st.chat_message("assistant"):
        st.success(f"🎉 本次模拟面试完成！共练习了 {total} 道题。")
    if st.button("🔄 重新开始"):
        for key in ["mock_started", "mock_questions", "mock_current_idx",
                    "mock_chat_history", "mock_waiting_answer", "mock_phase"]:
            del st.session_state[key]
        st.rerun()
    st.stop()

if st.session_state.mock_phase == "feedback_done":
    col_next, col_end = st.columns(2)
    with col_next:
        if st.button("下一题", type="primary"):
            st.session_state.mock_current_idx += 1
            st.session_state.mock_phase = "questioning"
            st.rerun()
    with col_end:
        if st.button("结束练习"):
            st.session_state.mock_current_idx = total
            st.rerun()
    st.stop()

# 用户输入
answer = st.chat_input("输入你的回答…")
if answer:
    st.session_state.mock_chat_history.append({
        "role": "user",
        "content": answer,
        "kind": "answer",
        "question_idx": current_idx,
    })

    with st.spinner("分析中…"):
        feedback_dict = analyze_mock_answer(
            question=current_q["question"],
            answer=answer,
            job_direction=st.session_state.mock_job_direction,
        )

    if "_error" in feedback_dict:
        feedback_text = feedback_dict["_error"]
        feedback_kind = "feedback_error"
    else:
        feedback_text = "\n\n".join(filter(None, [
            f"✅ **亮点**\n{feedback_dict.get('highlight', '')}",
            f"⚠️ **主要问题**\n{feedback_dict.get('problem', '')}",
            f"💡 **建议**\n{feedback_dict.get('suggestion', '')}",
            f"⭐ **评级**：{feedback_dict.get('grade', '')}",
        ]))
        feedback_kind = "feedback"

    st.session_state.mock_chat_history.append({
        "role": "assistant",
        "content": feedback_text,
        "kind": feedback_kind,
        "question_idx": current_idx,
    })

    # 更新掌握程度
    rating = extract_mock_rating(feedback_dict)
    new_mastery = RATING_TO_MASTERY.get(rating, "learning")
    update_mastery(current_q["id"], new_mastery)

    st.session_state.mock_phase = "feedback_done"
    st.rerun()
