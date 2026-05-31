"""
core/parser.py — 讯飞听见转写文件解析器

输入：讯飞听见导出的 .txt 文件路径
输出：InterviewSession dataclass
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# 尾部系统附加行关键词，匹配到即停止解析
_TAIL_PATTERNS = [
    "以上内容由AI生成",
    "仅供参考",
]

# 说话人头部行：「说话人X HH:MM:SS」或「说话人X MM:SS」
_SPEAKER_RE = re.compile(r"^(说话人\d+)\s+(\d{1,2}:\d{2}(?::\d{2})?)$")


def _default_role(speaker_label: str) -> str:
    """根据说话人标签返回默认角色。"""
    return "candidate" if speaker_label == "说话人1" else "interviewer"


@dataclass
class DialogueTurn:
    speaker: str    # "interviewer" 或 "candidate"
    timestamp: str  # 原始时间戳字符串
    content: str    # 发言内容


@dataclass
class InterviewSession:
    title: str                          # 文件标题（第一行）
    turns: list[DialogueTurn] = field(default_factory=list)
    candidate_turns: list[str] = field(default_factory=list)  # 仅候选人发言


def _is_tail_line(line: str) -> bool:
    """判断是否为尾部系统附加行。"""
    return any(kw in line for kw in _TAIL_PATTERNS)


def parse_file(
    path: str | Path,
    role_map: dict[str, str] | None = None,
) -> InterviewSession:
    """解析讯飞听见导出的 .txt 文件。

    Args:
        path: 转写文件路径。
        role_map: 可选的说话人角色覆盖映射，如 {"说话人1": "interviewer"}。
                  未指定时使用默认规则（说话人1=candidate，其余=interviewer）。

    Returns:
        InterviewSession，包含完整对话轮次和候选人发言列表。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 文件为空或无法识别标题行。
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"转写文件不存在：{path}")

    return parse_text(path.read_text(encoding="utf-8"), role_map=role_map)


def parse_text(
    text: str,
    role_map: dict[str, str] | None = None,
) -> InterviewSession:
    """从字符串内容解析讯飞听见导出的文本。

    Args:
        text: 转写文本内容。
        role_map: 可选的说话人角色覆盖映射，如 {"说话人1": "interviewer"}。
                  未指定时使用默认规则（说话人1=candidate，其余=interviewer）。

    Returns:
        InterviewSession，包含完整对话轮次和候选人发言列表。

    Raises:
        ValueError: 内容为空或无法识别标题行。
    """
    lines = text.splitlines()
    if not lines:
        raise ValueError("转写文本为空")

    # 第一行为标题
    title = lines[0].strip()
    if not title:
        raise ValueError("转写文本标题为空")

    session = InterviewSession(title=title)

    current_speaker_label: str | None = None
    current_timestamp: str = ""
    current_lines: list[str] = []

    def _flush() -> None:
        """将当前缓冲区的发言块写入 session。"""
        if current_speaker_label is None or not current_lines:
            return
        content = "\n".join(current_lines).strip()
        if not content:
            return
        role = (role_map or {}).get(current_speaker_label) or _default_role(current_speaker_label)
        turn = DialogueTurn(speaker=role, timestamp=current_timestamp, content=content)
        session.turns.append(turn)
        if role == "candidate":
            session.candidate_turns.append(content)

    for raw_line in lines[1:]:
        line = raw_line.strip()

        # 遇到尾部系统行，停止解析
        if _is_tail_line(line):
            break

        m = _SPEAKER_RE.match(line)
        if m:
            # 新说话人头部行：先 flush 上一块
            _flush()
            current_speaker_label = m.group(1)
            current_timestamp = m.group(2)
            current_lines = []
        elif line == "":
            # 空行：段落分隔，不 flush（同一说话人连续段落合并）
            continue
        else:
            # 正文内容行
            current_lines.append(line)

    # 处理最后一块
    _flush()

    return session
