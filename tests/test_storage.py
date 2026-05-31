"""
tests/test_storage.py — core/storage.py 单元测试

使用临时数据库，不污染 data/interviews.db。
"""

from __future__ import annotations

import pytest

from core.storage import init_db, save_session, list_sessions, get_session


@pytest.fixture
def db(tmp_path):
    """每个测试用独立的临时数据库路径。"""
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


# ── 1. 建表 ────────────────────────────────────────────────────────────────────

def test_init_db_creates_tables(db):
    """init_db 应创建 sessions 和 turns 两张表。"""
    import sqlite3
    conn = sqlite3.connect(db)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert "sessions" in tables
    assert "turns" in tables


def test_init_db_is_idempotent(db):
    """重复调用 init_db 不应报错（IF NOT EXISTS）。"""
    init_db(db)
    init_db(db)


# ── 2. 存储 ────────────────────────────────────────────────────────────────────

def test_save_session_returns_id(db):
    """save_session 应返回正整数 session_id。"""
    turns = [
        {"index": 1, "question": "请自我介绍", "answer": "我叫张三", "feedback": "良好"},
    ]
    session_id = save_session("测试面试", "AI应用开发", "整体表现良好", turns, db_path=db)
    assert isinstance(session_id, int)
    assert session_id > 0


def test_save_session_stores_all_turns(db):
    """save_session 应将所有轮次写入 turns 表，含 topic 字段。"""
    turns = [
        {"index": 1, "question": "问题一", "answer": "回答一", "feedback": "反馈一", "topic": "自我介绍"},
        {"index": 2, "question": "问题二", "answer": "回答二", "feedback": "反馈二", "topic": "技术深度"},
        {"index": 3, "question": "问题三", "answer": "回答三", "feedback": "反馈三", "topic": "技术深度"},
    ]
    session_id = save_session("多轮面试", "后端开发", "总结", turns, db_path=db)
    result = get_session(session_id, db)
    assert len(result["turns"]) == 3
    assert result["turns"][0]["topic"] == "自我介绍"
    assert result["turns"][1]["topic"] == "技术深度"


def test_save_multiple_sessions(db):
    """多次 save_session 应生成不同的 session_id。"""
    id1 = save_session("面试A", "产品经理", "总结A", [], db_path=db)
    id2 = save_session("面试B", "数据分析", "总结B", [], db_path=db)
    assert id1 != id2


# ── 3. 查询 ────────────────────────────────────────────────────────────────────

def test_list_sessions_returns_all(db):
    """list_sessions 应返回所有已保存的会话。"""
    save_session("面试一", "AI开发", "总结一", [], db_path=db)
    save_session("面试二", "AI开发", "总结二", [], db_path=db)
    sessions = list_sessions(db)
    assert len(sessions) == 2


def test_list_sessions_fields(db):
    """list_sessions 每条记录应含 id/title/job_direction/created_at。"""
    save_session("面试标题", "岗位方向", "总结", [], db_path=db)
    sessions = list_sessions(db)
    assert set(sessions[0].keys()) >= {"id", "title", "job_direction", "created_at"}


def test_list_sessions_ordered_by_created_at_desc(db):
    """list_sessions 应按创建时间倒序（同秒内按 id 倒序）返回。"""
    id1 = save_session("第一次", "方向", "总结", [], db_path=db)
    id2 = save_session("第二次", "方向", "总结", [], db_path=db)
    sessions = list_sessions(db)
    ids = [s["id"] for s in sessions]
    assert ids.index(id2) < ids.index(id1)


def test_get_session_returns_correct_data(db):
    """get_session 应返回正确的 session 字段和 turns 列表，含 topic 字段。"""
    turns = [
        {"index": 1, "question": "Q1", "answer": "A1", "feedback": "F1", "topic": "话题A"},
        {"index": 2, "question": "Q2", "answer": "A2", "feedback": "F2", "topic": "话题B"},
    ]
    session_id = save_session("面试标题", "AI方向", "整体总结", turns, db_path=db)
    result = get_session(session_id, db)

    assert result["title"] == "面试标题"
    assert result["job_direction"] == "AI方向"
    assert result["summary"] == "整体总结"
    assert len(result["turns"]) == 2
    assert result["turns"][0]["question"] == "Q1"
    assert result["turns"][1]["answer"] == "A2"
    assert result["turns"][0]["topic"] == "话题A"
    assert result["turns"][1]["topic"] == "话题B"


def test_get_session_turns_ordered_by_index(db):
    """get_session 返回的 turns 应按 turn_index 升序排列。"""
    turns = [
        {"index": 3, "question": "Q3", "answer": "A3", "feedback": "", "topic": ""},
        {"index": 1, "question": "Q1", "answer": "A1", "feedback": "", "topic": ""},
        {"index": 2, "question": "Q2", "answer": "A2", "feedback": "", "topic": ""},
    ]
    session_id = save_session("乱序面试", "方向", "总结", turns, db_path=db)
    result = get_session(session_id, db)
    indices = [t["turn_index"] for t in result["turns"]]
    assert indices == [1, 2, 3]


def test_get_session_not_found(db):
    """get_session 查询不存在的 id 应返回 None。"""
    assert get_session(9999, db) is None


# ── 4. 评分 ────────────────────────────────────────────────────────────────────

from core.storage import get_scores_history

_SAMPLE_SCORES = {
    "star_completeness":  {"score": 6, "reason": "STAR 基本完整"},
    "technical_depth":    {"score": 7, "reason": "技术理解较深"},
    "logical_clarity":    {"score": 5, "reason": "逻辑一般"},
    "proactiveness":      {"score": 4, "reason": "主动性不足"},
    "result_orientation": {"score": 8, "reason": "结果量化清晰"},
}


def test_save_session_with_scores(db):
    """save_session 传入 scores 时，5个评分字段应正确存储。"""
    session_id = save_session("评分面试", "AI开发", "总结", [], _SAMPLE_SCORES, db)
    result = get_session(session_id, db)
    assert result["score_star_completeness"] == 6
    assert result["score_technical_depth"] == 7
    assert result["score_logical_clarity"] == 5
    assert result["score_proactiveness"] == 4
    assert result["score_result_orientation"] == 8


def test_save_session_without_scores(db):
    """save_session scores=None 时，评分字段应为 NULL，不报错。"""
    session_id = save_session("无评分面试", "AI开发", "总结", [], None, db)
    result = get_session(session_id, db)
    assert result["score_star_completeness"] is None
    assert result["score_technical_depth"] is None
    assert result["score_logical_clarity"] is None
    assert result["score_proactiveness"] is None
    assert result["score_result_orientation"] is None


def test_get_scores_history_returns_only_scored(db):
    """get_scores_history 只返回5个评分字段全部不为 NULL 的记录。"""
    save_session("有评分", "AI开发", "总结A", [], _SAMPLE_SCORES, db)
    save_session("无评分", "AI开发", "总结B", [], None, db)
    history = get_scores_history(db)
    assert len(history) == 1
    assert history[0]["title"] == "有评分"
    assert history[0]["star_completeness"] == 6
    assert history[0]["technical_depth"] == 7


# ── 5. 题库 ────────────────────────────────────────────────────────────────────

from core.storage import add_question, list_questions, update_mastery, get_question


def test_add_question_returns_id(db):
    """add_question 应返回正整数 question_id。"""
    qid = add_question(None, "系统设计", "如何设计一个高并发系统？", db_path=db)
    assert isinstance(qid, int)
    assert qid > 0


def test_list_questions_returns_all(db):
    """list_questions 无过滤时应返回所有题目。"""
    add_question(None, "话题A", "问题一", db_path=db)
    add_question(None, "话题B", "问题二", db_path=db)
    questions = list_questions(db_path=db)
    assert len(questions) == 2


def test_list_questions_filter_by_mastery(db):
    """list_questions 传入 mastery 时只返回匹配的题目。"""
    qid = add_question(None, "话题A", "问题一", db_path=db)
    add_question(None, "话题B", "问题二", db_path=db)
    update_mastery(qid, "mastered", db_path=db)
    result = list_questions(mastery="mastered", db_path=db)
    assert len(result) == 1
    assert result[0]["id"] == qid
    new_result = list_questions(mastery="new", db_path=db)
    assert len(new_result) == 1


def test_update_mastery_success(db):
    """update_mastery 更新存在的题目应返回 True，且字段已更新。"""
    qid = add_question(None, "话题", "问题", db_path=db)
    ok = update_mastery(qid, "learning", db_path=db)
    assert ok is True
    q = get_question(qid, db_path=db)
    assert q["mastery"] == "learning"


def test_update_mastery_not_found(db):
    """update_mastery 更新不存在的 id 应返回 False。"""
    ok = update_mastery(9999, "mastered", db_path=db)
    assert ok is False


def test_get_question_returns_correct_data(db):
    """get_question 应返回正确的题目字段。"""
    qid = add_question(None, "系统设计", "如何限流？", "令牌桶算法", "hard", db_path=db)
    q = get_question(qid, db_path=db)
    assert q["topic"] == "系统设计"
    assert q["question"] == "如何限流？"
    assert q["reference_answer"] == "令牌桶算法"
    assert q["difficulty"] == "hard"
    assert q["mastery"] == "new"
    assert q["source_session_id"] is None