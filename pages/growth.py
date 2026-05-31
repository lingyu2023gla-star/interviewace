"""
pages/growth.py — 成长追踪页面

展示历史评分的雷达图和折线趋势图。
"""

import streamlit as st
import plotly.graph_objects as go

from core.storage import get_scores_history

st.set_page_config(page_title="成长追踪 · InterviewAce", page_icon="📈", layout="centered")
st.title("📈 成长追踪")

history = get_scores_history()

if len(history) < 2:
    st.info("至少需要2次面试记录才能查看成长趋势，继续加油！")
    st.stop()

_DIM_LABELS = {
    "star_completeness": "STAR完整度",
    "technical_depth": "技术深度",
    "logical_clarity": "表达逻辑",
    "proactiveness": "主动性",
    "result_orientation": "结果导向",
}
_DIMS = list(_DIM_LABELS.keys())
_LABELS = list(_DIM_LABELS.values())

# ── 图表一：最近一次雷达图 ─────────────────────────────────────────────────────

latest = history[-1]
radar_values = [latest[d] for d in _DIMS]
# 闭合雷达图
radar_values_closed = radar_values + [radar_values[0]]
labels_closed = _LABELS + [_LABELS[0]]

fig_radar = go.Figure(go.Scatterpolar(
    r=radar_values_closed,
    theta=labels_closed,
    fill="toself",
    name=latest["created_at"][:10],
    line_color="royalblue",
))
fig_radar.update_layout(
    title="最近一次面试能力分布",
    polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
    showlegend=False,
)
st.plotly_chart(fig_radar, use_container_width=True)

# ── 图表二：折线趋势图 ────────────────────────────────────────────────────────

dates = [r["created_at"][:10] for r in history]

fig_line = go.Figure()
for dim, label in _DIM_LABELS.items():
    values = [r[dim] for r in history]
    fig_line.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode="lines+markers",
        name=label,
    ))

fig_line.update_layout(
    title="各维度成长趋势",
    xaxis_title="面试日期",
    yaxis=dict(title="分数", range=[0, 10]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_line, use_container_width=True)