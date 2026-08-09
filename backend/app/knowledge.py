"""把视频转写解析成可检索的知识块（chunk）。

转写结构：开头有日期/关键词/文字记录 等头部，正文以 `00:00` 这类时间戳分行，
每个时间戳后跟一段相对独立的内容（通常对应一个子问题）。据此切块。
"""
import re
from typing import List, Dict

from . import config

TIMESTAMP_RE = re.compile(r"^\s*\d{2}:\d{2}\s*$")
HEADER_MARKER = "文字记录:"


def _read_transcript() -> str:
    with open(config.TRANSCRIPT_PATH, encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def parse_chunks(text: str) -> List[Dict[str, str]]:
    # 只取头部标记之后的内容
    if HEADER_MARKER in text:
        text = text.split(HEADER_MARKER, 1)[1]

    blocks: List[str] = []
    current: List[str] = []
    for line in text.splitlines():
        if TIMESTAMP_RE.match(line):
            if current:
                blocks.append("\n".join(current).strip())
                current = []
        else:
            s = line.strip()
            if s:
                current.append(s)
    if current:
        blocks.append("\n".join(current).strip())

    return [
        {"id": str(i), "text": b}
        for i, b in enumerate(blocks)
        if len(b) > 20  # 丢弃过短的片段
    ]


def load_chunks() -> List[Dict[str, str]]:
    try:
        return parse_chunks(_read_transcript())
    except FileNotFoundError:
        return []
    except Exception:
        return []


if __name__ == "__main__":
    chunks = load_chunks()
    print(f"共 {len(chunks)} 个知识块\n")
    for c in chunks[:3]:
        print(f"--- {c['id']} ---")
        print(c["text"][:120], "...\n")