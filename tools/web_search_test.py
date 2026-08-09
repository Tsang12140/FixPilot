"""No-network regression tests for DeepSeek V4 Flash web search."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from app import llm


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


def assert_true(condition, detail):
    if not condition:
        raise AssertionError(detail)


def test_official_gate_is_narrow():
    assert_true(
        llm.is_official_deepseek_web_search("https://api.deepseek.com", "deepseek-v4-flash"),
        "official DeepSeek V4 Flash was rejected",
    )
    assert_true(
        not llm.is_official_deepseek_web_search(
            "https://ark.cn-beijing.volces.com/api/v3/responses", "deepseek-v4-flash"
        ),
        "Ark endpoint must not receive FixPilot web-search requests",
    )
    assert_true(
        not llm.is_official_deepseek_web_search("https://api.deepseek.com", "deepseek-v4-pro"),
        "unsupported DeepSeek model was accepted",
    )


def test_payload_enables_only_the_supported_tool():
    normal = llm.build_responses_payload([{"role": "user", "content": "hello"}], "deepseek-v4-flash")
    searched = llm.build_responses_payload(
        [{"role": "system", "content": "policy"}, {"role": "user", "content": "hello"}],
        "deepseek-v4-flash",
        web_search=True,
    )
    assert_true("tools" not in normal and "tool_choice" not in normal, "normal Responses payload enabled a tool")
    assert_true(searched.get("tools") == [{"type": "web_search"}], "web-search tool payload is incorrect")
    assert_true(searched.get("tool_choice") == {"type": "web_search"}, "web search is not explicitly selected")
    assert_true(searched.get("instructions") == "policy", "system policy did not become instructions")


def test_search_request_uses_official_responses_and_labels_sources():
    original_post = llm.httpx.post
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse({
            "output": [
                {"type": "web_search_call", "status": "completed", "url": "https://example.com/search?q=graphics-driver"},
                {"type": "message", "content": [{"type": "output_text", "text": "这是检索后的回答。"}]},
            ]
        })

    try:
        llm.httpx.post = fake_post
        reply = "".join(llm.stream_chat(
            [{"role": "user", "content": "查一下显卡驱动兼容性"}],
            api_key="test-key", base_url="https://api.deepseek.com", model="deepseek-v4-flash", web_search=True,
        ))
    finally:
        llm.httpx.post = original_post

    assert_true(len(calls) == 1, "web search should make exactly one completed request")
    url, kwargs = calls[0]
    assert_true(url == "https://api.deepseek.com/responses", "web search did not force the official Responses endpoint")
    payload = kwargs.get("json") or {}
    assert_true(payload.get("stream") is False, "FixPilot must use a completed Responses request")
    assert_true(payload.get("tools") == [{"type": "web_search"}], "official request omitted web_search")
    assert_true("本轮已联网查资料。" in reply, "reply did not transparently label the search")
    assert_true("https://example.com/search?q=graphics-driver" in reply, "provider-returned source URL was not preserved")


def test_other_providers_fail_before_network_call():
    original_post = llm.httpx.post
    called = False

    def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("non-official provider reached the network")

    try:
        llm.httpx.post = fail_if_called
        try:
            list(llm.stream_chat(
                [{"role": "user", "content": "查资料"}], api_key="test-key",
                base_url="https://example.test/v1", model="anything", web_search=True,
            ))
        except ValueError as exc:
            assert_true("仅支持官方 DeepSeek V4 Flash" in str(exc), "unsupported-provider error was unclear")
        else:
            raise AssertionError("unsupported provider did not fail")
    finally:
        llm.httpx.post = original_post
    assert_true(not called, "unsupported provider attempted a request")

def test_client_one_turn_control_contract():
    static_root = os.path.join(ROOT, "backend", "static")
    with open(os.path.join(static_root, "index.html"), encoding="utf-8") as source_file:
        html = source_file.read()
    with open(os.path.join(static_root, "app.js"), encoding="utf-8") as source_file:
        app = source_file.read()
    with open(os.path.join(static_root, "style.css"), encoding="utf-8") as source_file:
        css = source_file.read()
    assert_true('id="webSearchBtn"' in html, "composer does not contain the explicit search control")
    assert_true("webSearch: useWebSearch" in app, "chat payload does not include the one-turn search flag")
    assert_true("const retry = { convId, text, content, webSearch: useWebSearch };" in app, "retry state does not preserve search intent")
    assert_true("setWebSearchRequested(false);" in app, "successful send does not reset one-turn search state")
    assert_true("hostname.toLowerCase() === 'api.deepseek.com'" in app, "client model gate is not host-specific")
    assert_true("platform_web_search" in open(os.path.join(ROOT, "backend", "app", "main.py"), encoding="utf-8").read(), "server does not expose actual platform web-search support")
    assert_true("platformWebSearchEnabled" in app, "client does not follow the server platform capability flag")
    assert_true('"model web . img send"' in css and '"web input img send"' in css, "desktop/mobile composer placement is missing")

TESTS = [
    ("W01", "official web-search gate accepts only DeepSeek V4 Flash", test_official_gate_is_narrow),
    ("W02", "Responses payload enables only explicit web_search", test_payload_enables_only_the_supported_tool),
    ("W03", "search uses official Responses endpoint and labels provider sources", test_search_request_uses_official_responses_and_labels_sources),
    ("W04", "unsupported provider fails before network access", test_other_providers_fail_before_network_call),
    ("W05", "client keeps search explicit, one-turn, and responsive", test_client_one_turn_control_contract),
]


def run_tests():
    results = []
    for case_id, name, test in TESTS:
        try:
            test()
            results.append({"id": case_id, "name": name, "status": "PASS"})
        except Exception as exc:
            results.append({"id": case_id, "name": name, "status": "FAIL", "detail": str(exc)})
    return results


def main():
    parser = argparse.ArgumentParser(description="FixPilot DeepSeek web-search regression tests")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = run_tests()
    failed = any(result["status"] != "PASS" for result in results)
    if args.json:
        print(json.dumps({"suite": "websearch", "results": results}, ensure_ascii=False))
    else:
        for result in results:
            suffix = f" ({result.get('detail')})" if result.get("detail") else ""
            print(f"[{result['id']}] {result['name']}: {result['status']}{suffix}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()