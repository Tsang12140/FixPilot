"""DeepSeek 大模型客户端（OpenAI 兼容 /chat/completions，流式返回）。"""
import json
from typing import Iterator, List, Dict

import httpx

from . import config

BASE_POLICY = """你是 FixPilot，一位专业的电脑故障排查助手。你的目标是像熟悉电脑的朋友一样，陪用户一步步定位问题，而不是用一篇长教程把人淹没。

【永久边界】
- 全程以中文回答，不使用 emoji 或装饰性圆点。
- 只能依据用户文字、OCR 识别出的图片文字和知识库内容判断；不能真正看图、远程操作电脑、读取硬件、运行命令或联网搜索。
- 不编造检查结果、菜单路径、知识库结论或确定原因。
- 回复默认简短，通常 100～150 字，最多 200 字。
- 不人身攻击、不辱骂、不因用户不懂术语而取笑对方。

【排版和收尾】
- 用短段落；操作步骤逐行写成「1. 」「2. 」，不要一次堆出完整教程。
- 关键结论用 **加粗**，真正需要注意的风险可用「>」提示。
- 正常问诊时，最后只问 1 个最有区分度的判断题，并在其后给 2～4 个可点选项。
- 只有极少数纯开放性对话才允许没有选项。
- 只要给可点选项，必须严格使用下面的格式：先单独一行写「选项：」，再让每个选项独占一行并按「1. 文字」到「4. 文字」编号。单个选项内不能换行、不能再出现编号、不能混入操作步骤；选项结束后不要再写额外的收尾句。
"""

DIAGNOSTIC_POLICY = """【问诊与诊断规则】
- 一次只推进一个关键判断：先说当前最可能方向，再问一个能区分主要原因、低风险且用户容易回答的问题。
- D0 信息不足：继续收集一个关键线索；D1 初步怀疑：使用「更像、可疑、先确认」；D2 可验证方向：只给一个低风险验证动作；D3 高度怀疑：才给针对性修复；D4 已验证：说明依据后给精简方案。
- 单一错误码、模块名、一次蓝屏或「网上说」都不是定论。没有对照或复现证据时，不能把可能原因说成根因。
- 优先顺序：观察 → 无损设置检查 → 可逆软件操作 → 驱动/安全模式验证 → 硬件检查 → 高风险不可逆操作。
- 知识库没覆盖时，明确说明「这个场景知识库里没有直接收录」，再给稳妥的通用排障方向，不假装已确认。
"""

SAFETY_POLICY = """【安全规则，优先级高于表达风格】
- R0 只读检查、重启、查看设置等低风险操作可直接指导。
- R1 卸载/回退驱动、禁用设备、系统还原等可逆操作：说明影响、保留恢复路径、一次只做一个动作。
- R2 注册表关键项、重装系统、删除/调整分区、BitLocker/TPM、批量删除、向故障盘写入：先确认目的、数据备份或恢复条件，明确风险，再让用户确认；缺少前提就停止继续给步骤。
- R3 刷 BIOS/固件、超频/电压、带电拆装、电源内部、鼓包电池、烧焦味、冒烟、进液、高压：不要给远程细节步骤。先建议断电、停止操作，必要时送专业维修。
- 出现重要数据、硬盘异响/不稳定、BitLocker、格式化、分区丢失、数据恢复时，先保护数据：不要让用户初始化、格式化、重建分区，或在故障盘安装恢复软件。
- 技术水平高也不能跳过风险提示、备份确认或停止指导条件。
"""

STYLE_POLICIES = {
    "normal": """【表达偏好：正常点】像一个懂电脑、说话利落的朋友。自然、专业、耐心；不用客服套话，不刻意展示人格，也不主动损用户。""",
    "roast": """【表达偏好：嘴毒点】你是会修电脑的损友，不是客服，也不是段子手。用户选这个模式是允许你嘴上不饶人，不是允许你耽误排障。
- 只有已经确认的、无损失且低级的乌龙，才在首句用一句具体、短促的损友式吐槽；随后立刻给正经判断和下一步。
- 吐槽必须针对已经确认的具体事实，不要用泛泛的“笑死、破案、神仙、兄弟、一波、早说了”。不夸用户，不宣布自己在毒舌，也不解释笑点。
- 可以尖一点，但只损这次乌龙，绝不损人的能力、智商、年龄、表达或焦虑。例如显示器没通电，可以说“显示器没通电，它今天只负责优雅地黑着。”
- 没有合适的已确认乌龙，就完全正常说话；不要硬塞梗。出现数据、硬件、安全风险或用户明显着急时，自动停止玩笑。""",
    "concise": """【表达偏好：少废话】结论优先，只给当前必要动作和一个判断题；少解释原理、不开玩笑，但绝不能省略风险、确认或关键路径。""",
}

ROAST_MEME_POLICY = """
[Easter-egg presentation rules]
- Use an easter egg only after a clearly confirmed, harmless low-level blunder. Never use one for uncertainty, confusion, urgency, data risk, hardware risk, or a complex fault.
- If an easter egg is appropriate, the very first characters must be exactly one marker: [JOKE:emotion]. Then start the actual reply on a new line. Never output [JOKE6], and never explain the marker, the meme, or the number 6.
- emotion must be one of: confused, facepalm, sweat, cool. The system randomly decides between showing 6 and a matching meme.
- The line after the marker must be one concrete roast about the confirmed event, then return to diagnosis immediately. Do not use generic internet catchphrases or write more than one roast line.
"""

LEVEL_POLICIES = {
    "beginner": "用户需要细一点的操作路径。术语首次出现时顺手解释，明确说在哪里点、做完应看到什么；不要默认知道 BIOS、安全模式或设备管理器。",
    "intermediate": "用户会折腾一些。常见术语可直接用，保留关键路径和必要的诊断理由，不必反复科普基础概念。",
    "advanced": "用户比较熟。直接说判断依据、验证对象和下一步排查，减少基础操作教学，但仍保持一次只推进一个判断。",
    "unknown": "不要把用户当小白或高手。采用通用、易懂的深度，必要术语做最少解释，再根据本轮表现临时适配。",
}


def build_profile_policy(profile: Dict = None, temporary_level: str = "unknown") -> str:
    profile = profile or {}
    level = profile.get("technical_level") or "unknown"
    source = profile.get("technical_level_source") or "inferred_pending"
    style = profile.get("response_style") or "normal"
    active_level = level if level != "unknown" else temporary_level
    if active_level not in LEVEL_POLICIES:
        active_level = "unknown"
    if style not in STYLE_POLICIES:
        style = "normal"
    style_policy = STYLE_POLICIES[style]
    if style == "roast":
        style_policy += ROAST_MEME_POLICY
    return "\n".join([
        "【当前用户画像】",
        f"技术水平：{level}；来源：{source}；本轮解释深度：{active_level}",
        LEVEL_POLICIES[active_level],
        style_policy,
    ])


def build_system_messages(profile: Dict = None, temporary_level: str = "unknown") -> List[Dict[str, str]]:
    """逻辑分层，运行时仍组装为普通 OpenAI 兼容 messages。"""
    return [
        {"role": "system", "content": BASE_POLICY},
        {"role": "system", "content": DIAGNOSTIC_POLICY},
        {"role": "system", "content": SAFETY_POLICY},
        {"role": "system", "content": build_profile_policy(profile, temporary_level)},
    ]


# 保留名称，避免旧调用方或外部脚本失效；实际聊天使用 build_system_messages。
SYSTEM_PROMPT = "\n\n".join([BASE_POLICY, DIAGNOSTIC_POLICY, SAFETY_POLICY])


def _build_context(texts: List[str]) -> str:
    if not texts:
        return "（本次未检索到相关知识块）"
    blocks = "\n\n".join(f"[片段]\n{t}" for t in texts)
    return f"以下是知识库中检索到的相关内容，请据此回答：\n\n{blocks}"


def normalize_api_key(api_key: str) -> str:
    """Accept raw keys and harmless copy/paste wrappers without changing the secret."""
    key = (api_key or "").strip()
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in {"\"", "'"}:
        key = key[1:-1].strip()
    return key


def api_endpoint_url(api_base: str) -> str:
    """Accept an API base, a Chat Completions URL, or a Responses API URL.

    A plain base keeps the historic /chat/completions behavior. Users who
    enter a full /responses endpoint opt in to the OpenAI Responses format.
    """
    url = (api_base or config.DEEPSEEK_BASE_URL).rstrip("/")
    if url.endswith("/chat/completions") or url.endswith("/responses"):
        return url
    return url + "/chat/completions"


def chat_completions_url(api_base: str) -> str:
    """Backward-compatible name for callers that expect the resolved URL."""
    return api_endpoint_url(api_base)


def is_responses_api_url(url: str) -> bool:
    """Whether the configured endpoint speaks the OpenAI Responses protocol."""
    return (url or "").rstrip("/").endswith("/responses")


def is_volcengine_ark_url(url: str) -> bool:
    return "ark.cn-beijing.volces.com" in (url or "").lower()


def system_https_proxy() -> str:
    """Read Windows' HTTPS proxy so Ark uses the same network route as desktop apps."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
            enabled = winreg.QueryValueEx(key, "ProxyEnable")[0]
            raw = str(winreg.QueryValueEx(key, "ProxyServer")[0] or "").strip()
        if not enabled or not raw:
            return ""
        selected = raw
        if "=" in raw:
            pairs = {}
            for item in raw.split(";"):
                if "=" in item:
                    name, value = item.split("=", 1)
                    pairs[name.strip().lower()] = value.strip()
            selected = pairs.get("https") or pairs.get("http") or ""
        if not selected:
            return ""
        return selected if "://" in selected else f"http://{selected}"
    except (ImportError, OSError):
        return ""


def provider_request_options(url: str) -> Dict:
    """Ark must use the user-configured system proxy, not inherited proxy variables."""
    if not is_volcengine_ark_url(url):
        return {}
    proxy = system_https_proxy()
    options = {"trust_env": False}
    if proxy:
        options["proxy"] = proxy
    return options


def build_chat_payload(messages: List[Dict[str, str]], model: str, url: str) -> Dict:
    """Build a conservative OpenAI-compatible request payload.

    Ark model capabilities differ by endpoint, so use only the required
    Chat Completions fields there. Other providers retain FixPilot's limits.
    """
    payload = {
        "model": model or config.DEEPSEEK_MODEL,
        "messages": messages,
        "stream": True,
    }
    if "ark.cn-beijing.volces.com" not in url.lower():
        payload.update({"temperature": 0.8, "max_tokens": 1500})
    return payload


def build_responses_payload(messages: List[Dict[str, str]], model: str) -> Dict:
    """Translate FixPilot's message list into the OpenAI Responses format.

    System policies become ``instructions`` so they retain their intended
    priority. Conversation turns are represented as typed input/output text.
    We deliberately do not enable the example's web_search tool: FixPilot has
    no tool-result loop and its product policy must not claim live web access.
    """
    instructions = []
    input_items = []
    for message in messages:
        role = message.get("role", "user")
        content = str(message.get("content", ""))
        if not content:
            continue
        if role == "system":
            instructions.append(content)
            continue
        if role == "assistant":
            # Ark validates historic assistant turns as completed message items.
            # Without this status, a first request works but the next turn fails
            # with: "missing input.status parameter".
            input_items.append({
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": content}],
            })
            continue
        input_items.append({
            "role": "user",
            "content": [{"type": "input_text", "text": content}],
        })

    payload = {
        "model": model or config.DEEPSEEK_MODEL,
        "stream": True,
        "input": input_items or [{
            "role": "user",
            "content": [{"type": "input_text", "text": "Hi"}],
        }],
    }
    if instructions:
        payload["instructions"] = "\n\n".join(instructions)
    return payload


def build_request_payload(messages: List[Dict[str, str]], model: str, url: str) -> Dict:
    if is_responses_api_url(url):
        return build_responses_payload(messages, model)
    return build_chat_payload(messages, model, url)


def test_chat_connection(
    api_key: str,
    base_url: str = "",
    model: str = "",
) -> None:
    """Test a user-supplied API and verify that it returns readable text."""
    url = api_endpoint_url(base_url)
    payload = build_request_payload([{"role": "user", "content": "Hi"}], model, url)
    payload["stream"] = False
    key = normalize_api_key(api_key)
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(timeout=30.0, connect=10.0)
    response = httpx.post(
        url, headers=headers, json=payload, timeout=timeout,
        **provider_request_options(url),
    )
    response.raise_for_status()
    body = response.json()
    if is_responses_api_url(url):
        if not extract_responses_output_text(body):
            raise RuntimeError("Responses API test succeeded but did not contain output text")
    elif not str(((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip():
        raise RuntimeError("Chat Completions API test succeeded but did not contain output text")


def extract_responses_output_text(body: Dict) -> str:
    """Return plain text from a completed OpenAI Responses API object."""
    top_level = body.get("output_text")
    if isinstance(top_level, str) and top_level.strip():
        return top_level.strip()
    parts = []
    for item in body.get("output") or []:
        for content in item.get("content") or []:
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text") or content.get("value") or ""
                if isinstance(text, str) and text:
                    parts.append(text)
    return "".join(parts).strip()


def stream_chat(
    messages: List[Dict[str, str]],
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> Iterator[str]:
    """Stream a displayable answer from the configured OpenAI-compatible API."""
    key = normalize_api_key(api_key or config.DEEPSEEK_API_KEY)
    url = api_endpoint_url(base_url)
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = build_request_payload(messages, model, url)
    request_options = provider_request_options(url)

    # The Ark Responses endpoint can keep a proxied SSE connection open without
    # ever sending a text delta. Ask it for one completed response instead, then
    # retain FixPilot's browser-side SSE protocol for a stable UI experience.
    if is_responses_api_url(url):
        payload["stream"] = False
        timeout = httpx.Timeout(timeout=45.0, connect=12.0)
        response = httpx.post(url, headers=headers, json=payload, timeout=timeout, **request_options)
        response.raise_for_status()
        text = extract_responses_output_text(response.json())
        if not text:
            raise RuntimeError("Responses API returned no displayable output text")
        yield text
        return

    timeout = httpx.Timeout(timeout=75.0, connect=12.0)
    with httpx.stream(
        "POST", url, headers=headers, json=payload, timeout=timeout,
        **request_options,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
                delta = chunk["choices"][0]["delta"].get("content", "")
                if delta:
                    yield delta
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
