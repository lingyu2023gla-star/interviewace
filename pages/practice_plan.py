import streamlit as st
from core.storage import get_scores_history, list_questions
from core.analyzer import generate_practice_plan

st.set_page_config(page_title="练习计划 · InterviewAce", page_icon="🎯", layout="centered")
st.title("🎯 维度强化计划")

DIM_LABELS = {
    "star_completeness": "STAR完整度",
    "technical_depth": "技术深度",
    "logical_clarity": "表达逻辑",
    "proactiveness": "主动性",
    "result_orientation": "结果导向",
}

DIM_KEYS = list(DIM_LABELS.keys())

# ── 数据准备 ──────────────────────────────────────────────────────────────────

history = get_scores_history()
if not history:
    st.info("暂无历史评分数据，请先完成至少一次面试复盘。")
    st.stop()

# 计算各维度平均分
dim_avg: dict[str, float] = {}
for dim in DIM_KEYS:
    scores = [r[dim] for r in history if r.get(dim) is not None]
    dim_avg[dim] = round(sum(scores) / len(scores), 1) if scores else 0.0

# 找出弱项维度（平均分 < 7，按分数升序）
weak_dimensions = [
    {"dimension": dim, "label": DIM_LABELS[dim], "avg_score": dim_avg[dim]}
    for dim in DIM_KEYS
    if dim_avg[dim] < 7
]
weak_dimensions.sort(key=lambda x: x["avg_score"])

# 取未掌握题目，按话题分组
all_questions = list_questions(mastery="new") + list_questions(mastery="learning")
questions_by_topic: dict[str, list[dict]] = {}
for q in all_questions:
    topic = q.get("topic", "其他")
    questions_by_topic.setdefault(topic, []).append(q)

# ── 维度总览 ──────────────────────────────────────────────────────────────────

st.subheader("📊 当前维度评分")
cols = st.columns(5)
for i, dim in enumerate(DIM_KEYS):
    score = dim_avg[dim]
    delta_color = "normal" if score >= 7 else "inverse"
    cols[i].metric(
        label=DIM_LABELS[dim],
        value=f"{score}/10",
        delta="良好" if score >= 7 else "需强化",
        delta_color=delta_color,
    )

if not weak_dimensions:
    st.success("🎉 所有维度均在 7 分以上，整体表现良好！继续保持。")
    st.stop()

st.divider()

# ── 生成计划 ──────────────────────────────────────────────────────────────────

job_direction = st.text_input(
    "目标岗位方向",
    placeholder="如：AI应用开发工程师、产品经理",
)

if not job_direction.strip():
    st.warning("请输入目标岗位方向后生成计划。")
    st.stop()

if st.button("🚀 生成强化计划", type="primary"):
    with st.spinner("正在分析弱项，生成定向强化计划…"):
        plan_data = generate_practice_plan(
            weak_dimensions=weak_dimensions,
            questions_by_topic=questions_by_topic,
            job_direction=job_direction.strip(),
        )

    if plan_data is None:
        st.error("计划生成失败，请重试。")
        st.stop()

    st.success(f"💡 {plan_data['summary']}")
    st.divider()

    for plan in plan_data["plans"]:
        label = plan["label"]
        score = plan["score"]
        with st.expander(f"{'🔴' if score < 5 else '🟡'} {label}（当前 {score}/10）", expanded=True):
            st.markdown(f"**问题诊断**\n{plan['diagnosis']}")
            st.markdown(f"**练习方法**\n{plan['action']}")

            focus_topics = plan.get("focus_topics", [])
            if focus_topics:
                st.markdown("**推荐练习题目**")
                for topic in focus_topics:
                    qs = questions_by_topic.get(topic, [])
                    if qs:
                        for q in qs[:3]:  # 每话题最多展示3题
                            difficulty_icon = {"easy": "⚪", "medium": "🟠", "hard": "🔴"}.get(q["difficulty"], "⚪")
                            st.markdown(f"{difficulty_icon} {q['question'][:60]}{'…' if len(q['question']) > 60 else ''}")
                    else:
                        st.caption(f"「{topic}」暂无未掌握题目")
