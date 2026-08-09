"""编排层：检索相关知识块 -> 组装提示词 -> 流式调用 DeepSeek。"""
from typing import Dict, Iterator, List
import re

from . import config, llm, official_sources, retriever
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
            iu = part.get("image_url")
            url = iu.get("url", "") if isinstance(iu, dict) else (iu or "")
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


def validate_client_messages(messages: List[Dict]) -> List[Dict]:
    """Accept exactly one current user message from the public chat API.

    Conversation history is server-owned. Allowing a client to submit an
    ``assistant`` or ``system`` role would let it rewrite the model context.
    """
    if not isinstance(messages, list) or len(messages) != 1:
        raise ValueError("每次只能提交一条用户消息")
    message = messages[0]
    if not isinstance(message, dict) or message.get("role") != "user":
        raise ValueError("请求只能包含当前用户消息")
    content = message.get("content")
    if not isinstance(content, (str, list)):
        raise ValueError("消息内容格式不正确")
    if isinstance(content, str) and not content.strip():
        raise ValueError("消息不能为空")
    if isinstance(content, list) and not content:
        raise ValueError("消息不能为空")
    return [{"role": "user", "content": content}]


def normalize_messages(messages: List[Dict]) -> List[Dict]:
    """把可能含图片的消息统一转成纯文本消息，供 DeepSeek 使用。"""
    seen: set = set()
    out: List[Dict] = []
    for m in messages:
        role = m.get("role")
        if role not in {"user", "assistant"}:
            continue
        content = _content_to_text(m.get("content"), seen)
        # UI-only easter-egg messages must not become model conversation context.
        if role == "assistant" and (content == "6" or re.fullmatch(r"\[MEME:[a-z_]+\]", content)):
            continue
        out.append({"role": role, "content": content})
    return out


def chat_stream(
    messages: List[Dict[str, str]],
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    profile: Dict = None,
    temporary_level: str = "unknown",
    already_normalized: bool = False,
) -> Iterator[str]:
    """messages: 完整对话历史（不含 system）。可含 OpenAI 多模态图片消息。

    可选 api_key / base_url / model 透传给 llm.stream_chat（用户自带 Key）。
    """
    normalized = messages if already_normalized else normalize_messages(messages)

    # 用最近一条用户消息作为检索关键字
    query = ""
    for m in reversed(normalized):
        if m.get("role") == "user":
            query = m["content"]
            break

    hits = retriever.retrieve(query)
    context = llm._build_context([h["text"] for h in hits])

    registry_query = "\n".join(
        str(message.get("content", ""))
        for message in normalized[-8:]
        if message.get("role") == "user"
    )
    lookup_sources = official_sources.select_official_sources(registry_query)
    official_lookup_available = bool(lookup_sources) and llm.is_official_deepseek_web_search(
        base_url, model or config.DEEPSEEK_MODEL
    )
    allowed_source_domains = official_sources.allowed_domains(lookup_sources)
    full = llm.build_system_messages(profile, temporary_level)
    if official_lookup_available:
        full.append({"role": "system", "content": llm.OFFICIAL_LOOKUP_POLICY})
        full.append({"role": "system", "content": official_sources.build_lookup_policy(lookup_sources)})
    full.extend(normalized)
    # 把检索到的知识上下文插入最后一条用户消息之前，作为 system 提示
    full.insert(max(1, len(full) - 1), {"role": "system", "content": context})

    yield from llm.stream_chat(
        full, api_key=api_key, base_url=base_url, model=model,
        official_lookup_available=official_lookup_available,
        allowed_source_domains=allowed_source_domains,
    )
