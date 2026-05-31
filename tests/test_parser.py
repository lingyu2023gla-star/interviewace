"""
tests/test_parser.py — core/parser.py 单元测试
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from core.parser import DialogueTurn, InterviewSession, parse_file


def _write_fixture(tmp_path: Path, content: str) -> Path:
    """将内容写入临时文件并返回路径。"""
    f = tmp_path / "interview.txt"
    f.write_text(textwrap.dedent(content), encoding="utf-8")
    return f


# ── 1. 正常解析 ────────────────────────────────────────────────────────────────

def test_normal_parse(tmp_path: Path) -> None:
    """正常解析：标题、说话人角色、时间戳、内容均正确。"""
    f = _write_fixture(tmp_path, """\
        AI技术在财务管理与面试中的应用
        说话人2 00:00
        请介绍一下你自己。

        说话人1 00:23
        我叫张三，有三年后端开发经验。

        说话人2 00:45
        你最擅长的技术栈是什么？

        说话人1 01:02
        主要是 Python 和 Go。
    """)

    session = parse_file(f)

    assert session.title == "AI技术在财务管理与面试中的应用"
    assert len(session.turns) == 4

    assert session.turns[0] == DialogueTurn(
        speaker="interviewer", timestamp="00:00", content="请介绍一下你自己。"
    )
    assert session.turns[1] == DialogueTurn(
        speaker="candidate", timestamp="00:23", content="我叫张三，有三年后端开发经验。"
    )
    assert session.turns[2].speaker == "interviewer"
    assert session.turns[3].speaker == "candidate"

    assert session.candidate_turns == [
        "我叫张三，有三年后端开发经验。",
        "主要是 Python 和 Go。",
    ]


def test_timestamp_hhmmss(tmp_path: Path) -> None:
    """支持 HH:MM:SS 格式时间戳。"""
    f = _write_fixture(tmp_path, """\
        面试记录
        说话人1 01:02:03
        回答内容。
    """)
    session = parse_file(f)
    assert session.turns[0].timestamp == "01:02:03"


def test_multiline_content_merged(tmp_path: Path) -> None:
    """同一说话人连续多段文字合并为一个发言块。"""
    f = _write_fixture(tmp_path, """\
        面试记录
        说话人1 00:10
        第一段内容。

        第二段内容。
    """)
    session = parse_file(f)
    assert len(session.turns) == 1
    assert "第一段内容。" in session.turns[0].content
    assert "第二段内容。" in session.turns[0].content


# ── 2. 说话人角色切换 ──────────────────────────────────────────────────────────

def test_role_map_override(tmp_path: Path) -> None:
    """通过 role_map 手动切换说话人角色。"""
    f = _write_fixture(tmp_path, """\
        面试记录
        说话人1 00:00
        这是面试官的问题。

        说话人2 00:10
        这是候选人的回答。
    """)
    # 反转默认角色
    session = parse_file(f, role_map={"说话人1": "interviewer", "说话人2": "candidate"})

    assert session.turns[0].speaker == "interviewer"
    assert session.turns[1].speaker == "candidate"
    assert session.candidate_turns == ["这是候选人的回答。"]


def test_default_role_speaker1_is_candidate(tmp_path: Path) -> None:
    """默认规则：说话人1 → candidate，说话人2 → interviewer。"""
    f = _write_fixture(tmp_path, """\
        面试记录
        说话人1 00:00
        候选人发言。

        说话人2 00:05
        面试官发言。

        说话人3 00:10
        第三方发言（也映射为 interviewer）。
    """)
    session = parse_file(f)
    assert session.turns[0].speaker == "candidate"
    assert session.turns[1].speaker == "interviewer"
    assert session.turns[2].speaker == "interviewer"


# ── 3. 尾部过滤 ────────────────────────────────────────────────────────────────

def test_tail_filter_ai_generated(tmp_path: Path) -> None:
    """过滤「以上内容由AI生成，仅供参考」尾部行，不计入对话。"""
    f = _write_fixture(tmp_path, """\
        面试记录
        说话人2 00:00
        请自我介绍。

        说话人1 00:10
        我是候选人。

        以上内容由AI生成，仅供参考
        这行不应被解析。
    """)
    session = parse_file(f)
    assert len(session.turns) == 2
    assert all("以上内容" not in t.content for t in session.turns)


def test_tail_filter_stops_at_keyword(tmp_path: Path) -> None:
    """尾部关键词出现后，后续所有行均被忽略。"""
    f = _write_fixture(tmp_path, """\
        面试记录
        说话人1 00:00
        正常发言。

        仅供参考
        说话人2 00:30
        这段不应出现。
    """)
    session = parse_file(f)
    assert len(session.turns) == 1
    assert session.turns[0].content == "正常发言。"


# ── 4. 边界情况 ────────────────────────────────────────────────────────────────

def test_file_not_found() -> None:
    """文件不存在时抛出 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        parse_file("/nonexistent/path/interview.txt")


def test_empty_file(tmp_path: Path) -> None:
    """空文件抛出 ValueError。"""
    f = tmp_path / "empty.txt"
    f.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_file(f)