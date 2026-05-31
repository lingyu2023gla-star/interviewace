"""
core/storage.py — SQLite 读写

数据库路径：data/interviews.db（运行时自动建表）
所有操作通过 context manager 管理连接，不暴露 connection 对象。
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

DB_PATH = "data/interviews.db"


@contextmanager
def _connect(db_path: str = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """打开 SQLite 连接，自动提交或回滚，用完关闭。"""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = DB_PATH) -> None:
    """建表（幂等，已存在则跳过）。app 启动时调用一次。"""
    with _connect(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                title                    TEXT    NOT NULL,
                job_direction            TEXT    NOT NULL,
                created_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                summary                  TEXT,
                score_star_completeness  INTEGER DEFAULT NULL,
                score_technical_depth    INTEGER DEFAULT NULL,
                score_logical_clarity    INTEGER DEFAULT NULL,
                score_proactiveness      INTEGER DEFAULT NULL,
                score_result_orientation INTEGER DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS turns (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                turn_index INTEGER NOT NULL,
                question   TEXT    NOT NULL,
                answer     TEXT    NOT NULL,
                feedback   TEXT,
                topic      TEXT    DEFAULT ''
            );
        """)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS questions (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                source_session_id INTEGER REFERENCES sessions(id),
                topic             TEXT    NOT NULL,
                question          TEXT    NOT NULL,
                reference_answer  TEXT    DEFAULT '',
                difficulty        TEXT    DEFAULT 'medium',
                mastery           TEXT    DEFAULT 'new',
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # 兼容已有数据库：字段已存在时 SQLite 会报错，忽略即可
        for col in [
            "ALTER TABLE turns ADD COLUMN topic TEXT DEFAULT ''",
            "ALTER TABLE sessions ADD COLUMN score_star_completeness INTEGER DEFAULT NULL",
            "ALTER TABLE sessions ADD COLUMN score_technical_depth INTEGER DEFAULT NULL",
            "ALTER TABLE sessions ADD COLUMN score_logical_clarity INTEGER DEFAULT NULL",
            "ALTER TABLE sessions ADD COLUMN score_proactiveness INTEGER DEFAULT NULL",
            "ALTER TABLE sessions ADD COLUMN score_result_orientation INTEGER DEFAULT NULL",
        ]:
            try:
                conn.execute(col)
            except Exception:
                pass


def save_session(
    title: str,
    job_direction: str,
    summary: str,
    turns: list[dict],
    scores: dict | None = None,
    db_path: str = DB_PATH,
) -> int:
    """保存一次面试会话及所有轮次问答。

    Args:
        title: 转写文件标题。
        job_direction: 岗位方向。
        summary: 整体复盘总结。
        turns: 每轮数据，每个 dict 含 index/question/answer/feedback/topic。
        scores: score_session 的返回值，None 时评分字段存 NULL。

    Returns:
        新建 session 的 id。
    """
    def _score(key: str) -> int | None:
        if scores is None:
            return None
        item = scores.get(key)
        return item.get("score") if isinstance(item, dict) else None

    with _connect(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO sessions
               (title, job_direction, summary,
                score_star_completeness, score_technical_depth,
                score_logical_clarity, score_proactiveness,
                score_result_orientation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                title, job_direction, summary,
                _score("star_completeness"),
                _score("technical_depth"),
                _score("logical_clarity"),
                _score("proactiveness"),
                _score("result_orientation"),
            ),
        )
        session_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO turns (session_id, turn_index, question, answer, feedback, topic) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (session_id, t["index"], t["question"], t["answer"], t.get("feedback", ""), t.get("topic", ""))
                for t in turns
            ],
        )
    return session_id


def list_sessions(db_path: str = DB_PATH) -> list[dict]:
    """返回所有会话列表，按创建时间倒序。

    Returns:
        每条记录含 id / title / job_direction / created_at。
    """
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, title, job_direction, created_at FROM sessions ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_session(session_id: int, db_path: str = DB_PATH) -> dict | None:
    """返回单个会话及其所有轮次。

    Args:
        session_id: 会话 id。

    Returns:
        含 session 字段和 turns 列表的 dict；不存在时返回 None。
    """
    with _connect(db_path) as conn:
        session_row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if session_row is None:
            return None
        turns_rows = conn.execute(
            "SELECT turn_index, question, answer, feedback, topic FROM turns WHERE session_id = ? ORDER BY turn_index",
            (session_id,),
        ).fetchall()
    return {
        **dict(session_row),
        "turns": [dict(row) for row in turns_rows],
    }


def add_question(
    source_session_id: int | None,
    topic: str,
    question: str,
    reference_answer: str = "",
    difficulty: str = "medium",
    db_path: str = DB_PATH,
) -> int:
    """向题库新增一道题。

    Returns:
        新建 question 的 id。
    """
    with _connect(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO questions (source_session_id, topic, question, reference_answer, difficulty)
               VALUES (?, ?, ?, ?, ?)""",
            (source_session_id, topic, question, reference_answer, difficulty),
        )
    return cursor.lastrowid


def list_questions(mastery: str | None = None, db_path: str = DB_PATH) -> list[dict]:
    """返回题库列表，按创建时间倒序。

    Args:
        mastery: 若指定，只返回该掌握程度的题目（'new'/'learning'/'mastered'）。

    Returns:
        每条记录含全部 questions 字段。
    """
    with _connect(db_path) as conn:
        if mastery is None:
            rows = conn.execute(
                "SELECT * FROM questions ORDER BY created_at DESC, id DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM questions WHERE mastery = ? ORDER BY created_at DESC, id DESC",
                (mastery,),
            ).fetchall()
    return [dict(row) for row in rows]


def update_mastery(question_id: int, mastery: str, db_path: str = DB_PATH) -> bool:
    """更新题目的掌握程度。

    Args:
        question_id: 题目 id。
        mastery: 新的掌握程度（'new'/'learning'/'mastered'）。

    Returns:
        True 表示更新成功；False 表示 id 不存在。
    """
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "UPDATE questions SET mastery = ? WHERE id = ?",
            (mastery, question_id),
        )
    return cursor.rowcount > 0


def get_question(question_id: int, db_path: str = DB_PATH) -> dict | None:
    """返回单道题目详情。

    Returns:
        含全部 questions 字段的 dict；不存在时返回 None。
    """
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM questions WHERE id = ?", (question_id,)
        ).fetchone()
    return dict(row) if row is not None else None


def get_scores_history(db_path: str = DB_PATH) -> list[dict]:
    """返回所有有完整评分记录的会话，按 created_at 升序（用于折线图）。

    Returns:
        每条记录含 session_id / title / created_at 及5个评分字段。
        只返回5个分数字段全部不为 NULL 的记录。
    """
    with _connect(db_path) as conn:
        rows = conn.execute(
            """SELECT
                id AS session_id,
                title,
                created_at,
                score_star_completeness  AS star_completeness,
                score_technical_depth    AS technical_depth,
                score_logical_clarity    AS logical_clarity,
                score_proactiveness      AS proactiveness,
                score_result_orientation AS result_orientation
               FROM sessions
               WHERE score_star_completeness  IS NOT NULL
                 AND score_technical_depth    IS NOT NULL
                 AND score_logical_clarity    IS NOT NULL
                 AND score_proactiveness      IS NOT NULL
                 AND score_result_orientation IS NOT NULL
               ORDER BY created_at ASC, id ASC"""
        ).fetchall()
    return [dict(row) for row in rows]