"""
pages/question_bank.py — 面试题库页面

展示从历次面试中沉淀的题目，支持按掌握程度分 tab 浏览和更新。
"""

import streamlit as st
from core.storage import list_questions, update_mastery

st.set_page_config(page_title="面试题库 · InterviewAce", page_icon="📚", layout="centered")
st.title("📚 面试题库")

MASTERY_LABELS = {
    "new": "🔴 未掌握",
    "learning": "🟡 练习中",
    "mastered": "🟢 已掌握",
}
DIFFICULTY_LABELS = {
    "easy": "⚪ 简单",
    "medium": "🟠 中等",
    "hard": "🔴 困难",
}

# 三个 tab
tab1, tab2, tab3 = st.tabs(["🔴 待练习", "🟢 已掌握", "📋 全部"])


def render_questions(questions: list[dict]):
    """渲染题目列表，每道题一个 expander。"""
    if not questions:
        st.caption("暂无题目")
        return
    for q in questions:
        label = f"{DIFFICULTY_LABELS.get(q['difficulty'], '')}  {q['topic']} — {q['question'][:30]}{'…' if len(q['question']) > 30 else ''}"
        with st.expander(label):
            st.markdown("**面试问题**")
            st.info(q["question"])
            if q.get("reference_answer"):
                st.markdown("**参考答案框架**")
                st.success(q["reference_answer"])
            st.markdown("**掌握程度**")
            cols = st.columns(3)
            for i, (mastery_key, mastery_label) in enumerate(MASTERY_LABELS.items()):
                is_current = q["mastery"] == mastery_key
                if cols[i].button(
                    mastery_label if not is_current else f"**{mastery_label} ✓**",
                    key=f"mastery_{q['id']}_{mastery_key}",
                    disabled=is_current,
                ):
                    update_mastery(q["id"], mastery_key)
                    st.rerun()


with tab1:
    questions = list_questions(mastery="new") + list_questions(mastery="learning")
    st.caption(f"共 {len(questions)} 道待练习题目")
    render_questions(questions)

with tab2:
    questions = list_questions(mastery="mastered")
    st.caption(f"共 {len(questions)} 道已掌握题目")
    render_questions(questions)

with tab3:
    all_questions = list_questions()
    st.caption(f"共 {len(all_questions)} 道题目")
    # 话题筛选
    topics = sorted(set(q["topic"] for q in all_questions))
    selected = st.selectbox("按话题筛选", ["全部"] + topics)
    filtered = all_questions if selected == "全部" else [q for q in all_questions if q["topic"] == selected]
    render_questions(filtered)