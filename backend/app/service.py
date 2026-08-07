"""编排层：检索相关知识块 -> 组装提示词 -> 流式调用 DeepSeek。"""
from typing import Dict, Iterator, List

from . import llm, retriever
from . import ocr


def _content_to_text(content, seen: set) -> str:
    """把消息 content 转成纯文本。

    字符串直接返回；多模态数组会调用 OCR 把 image_url 转成文字，
    web/images 网络图片（无 base64）则补一个说明。
    """
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts_text: List[str] = []
    image_texts: List[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        t = part.get("type")
        if t == "text":
            parts_text.append(part.get("text", ""))
        elif t == "image_url":
            url = (part.get("image_url") or {}).get("url", "")
            if url.startswith("data:image") and url not in seen:
                seen.add(url)
                try:
                    txt = ocr.image_to_text(url)
                    if txt.strip():
                        image_texts.append(txt)
                    else:
                        image_texts.append("（图片中未识别到文字）")
                except Exception as e:  # OCR 失败不阻断对话
                    image_texts.append(f"（图片识别失败：{e}）")
            else:
                image_texts.append("（用户上传了一张图片）")

    # 图片识别结果标注来源，帮助模型理解
    if image_texts:
        labeled = [f"[用户上传图片中的文字]\n{t}" for t in image_texts]
        return "\n\n".join(labeled + parts_text)
    return "\n".join(parts_text)


def _normalize_messages(messages: List[Dict]) -> List[Dict]:
    """把可能含图片的消息统一转成纯文本消息，供 DeepSeek 使用。"""
    seen: set = set()
    out: List[Dict] = []
    for m in messages:
        role = m.get("role")
        content = _content_to_text(m.get("content"), seen)
        out.append({"role": role, "content": content})
    return out


def chat_stream(messages: List[Dict[str, str]]) -> Iterator[str]:
    """messages: 完整对话历史（不含 system）。可含 OpenAI 多模态图片消息。"""
    normalized = _normalize_messages(messages)

    # 用最近一条用户消息作为检索关键字
    query = ""
    for m in reversed(normalized):
        if m.get("role") == "user":
            query = m["content"]
            break

    hits = retriever.retrieve(query)
    context = llm._build_context([h["text"] for h in hits])

    full = [{"role": "system", "content": llm.SYSTEM_PROMPT}]
    full.extend(normalized)
    # 把检索到的知识上下文插入最后一条用户消息之前，作为 system 提示
    full.insert(max(1, len(full) - 1), {"role": "system", "content": context})

    yield from llm.stream_chat(full)