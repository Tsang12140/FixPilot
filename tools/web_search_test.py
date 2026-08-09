"""No-network regression tests for automatic official-reference lookup."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from app import llm, official_sources, service


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
        "Ark endpoint must not receive FixPilot official lookup",
    )
    assert_true(
        not llm.is_official_deepseek_web_search("https://api.deepseek.com", "deepseek-v4-pro"),
        "unsupported DeepSeek model was accepted",
    )


def test_payload_makes_lookup_available_without_forcing_it():
    normal = llm.build_responses_payload([{"role": "user", "content": "hello"}], "deepseek-v4-flash")
    allowed = llm.build_responses_payload(
        [{"role": "system", "content": "policy"}, {"role": "user", "content": "hello"}],
        "deepseek-v4-flash",
        official_lookup_available=True,
    )
    assert_true("tools" not in normal and "tool_choice" not in normal, "normal payload enabled a tool")
    assert_true(allowed.get("tools") == [{"type": "web_search"}], "lookup tool payload is incorrect")
    assert_true("tool_choice" not in allowed, "lookup must remain model-decided")
    assert_true(allowed.get("instructions") == "policy", "system policy did not become instructions")


def test_actual_lookup_uses_official_responses_and_discloses_sources():
    original_post = llm.httpx.post
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse({
            "output": [
                {"type": "web_search_call", "status": "completed", "url": "https://vendor.example/manual.pdf"},
                {"type": "message", "content": [{"type": "output_text", "text": "official answer"}]},
            ]
        })

    try:
        llm.httpx.post = fake_post
        reply = "".join(llm.stream_chat(
            [{"role": "user", "content": "Need the vendor manual"}],
            api_key="test-key", base_url="https://api.deepseek.com", model="deepseek-v4-flash",
            official_lookup_available=True,
        ))
    finally:
        llm.httpx.post = original_post

    assert_true(len(calls) == 1, "official lookup should make one completed request")
    url, kwargs = calls[0]
    assert_true(url == "https://api.deepseek.com/responses", "lookup did not use the official Responses endpoint")
    payload = kwargs.get("json") or {}
    assert_true(payload.get("stream") is False, "Responses lookup must be completed server-side")
    assert_true(payload.get("tools") == [{"type": "web_search"}], "official request omitted web_search")
    assert_true(reply.startswith("\u672c\u8f6e\u67e5\u9605\u4e86\u5916\u90e8\u8d44\u6599\u3002"), "actual lookup was not transparently disclosed")
    assert_true("official answer" in reply, "answer text was lost")
    assert_true("https://vendor.example/manual.pdf" in reply, "provider-returned source URL was not preserved")


def test_normal_answer_has_no_lookup_disclosure_when_model_did_not_search():
    body = {"output": [{"type": "message", "content": [{"type": "output_text", "text": "normal reply"}]}]}
    reply = llm.append_web_search_sources("normal reply", body)
    assert_true(reply == "normal reply", "ordinary answer incorrectly exposed a no-search banner")


def test_non_official_provider_fails_before_network_when_lookup_is_requested_internally():
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
                [{"role": "user", "content": "manual"}], api_key="test-key",
                base_url="https://example.test/v1", model="anything", official_lookup_available=True,
            ))
        except ValueError as exc:
            assert_true("Official external lookup requires" in str(exc), "unsupported-provider error was unclear")
        else:
            raise AssertionError("unsupported provider did not fail")
    finally:
        llm.httpx.post = original_post
    assert_true(not called, "unsupported provider attempted a request")


def test_service_prioritizes_registry_without_turning_it_into_a_wall():
    original_retrieve = service.retriever.retrieve
    original_context = service.llm._build_context
    original_stream = service.llm.stream_chat
    captures = []

    def fake_stream(messages, **kwargs):
        captures.append((messages, kwargs))
        yield "ok"

    try:
        service.retriever.retrieve = lambda _query: []
        service.llm._build_context = lambda _items: ""
        service.llm.stream_chat = fake_stream
        list(service.chat_stream(
            [{"role": "user", "content": "asus B650M-PLUS BIOS manual"}],
            api_key="test-key", base_url="https://api.deepseek.com", model="deepseek-v4-flash",
        ))
        list(service.chat_stream(
            [{"role": "user", "content": "computer blue screen"}],
            api_key="test-key", base_url="https://api.deepseek.com", model="deepseek-v4-flash",
        ))
        list(service.chat_stream(
            [{"role": "user", "content": "acme X1234 firmware manual"}],
            api_key="test-key", base_url="https://api.deepseek.com", model="deepseek-v4-flash",
        ))
        list(service.chat_stream(
            [{"role": "user", "content": "asus B650M-PLUS BIOS manual"}],
            api_key="test-key", base_url="https://example.test/v1", model="anything",
        ))
    finally:
        service.retriever.retrieve = original_retrieve
        service.llm._build_context = original_context
        service.llm.stream_chat = original_stream

    official_messages, official_kwargs = captures[0]
    generic_messages, generic_kwargs = captures[1]
    unlisted_messages, unlisted_kwargs = captures[2]
    other_messages, other_kwargs = captures[3]
    assert_true(official_kwargs.get("official_lookup_available") is True, "matched official source was not granted internal lookup")
    assert_true(official_kwargs.get("preferred_source_domains") == {"asus.com", "asus.com.cn"}, "registry domains were not passed as preferred sources")
    assert_true(generic_kwargs.get("official_lookup_available") is False, "generic symptom incorrectly enabled lookup")
    assert_true(unlisted_kwargs.get("official_lookup_available") is True, "concrete unlisted manual request was not granted lookup")
    assert_true(unlisted_kwargs.get("preferred_source_domains") == set(), "unlisted request unexpectedly had preferred registry domains")
    assert_true(other_kwargs.get("official_lookup_available") is False, "unsupported provider was granted internal lookup")
    assert_true(any(message.get("content") == llm.OFFICIAL_LOOKUP_POLICY for message in official_messages), "official rule was not injected")
    assert_true(any("Registry-prioritized external lookup" in message.get("content", "") for message in official_messages), "priority rule was not injected")
    assert_true(not any(message.get("content") == llm.OFFICIAL_LOOKUP_POLICY for message in generic_messages), "official rule leaked to a generic symptom")
    assert_true(any(message.get("content") == llm.OFFICIAL_LOOKUP_POLICY for message in unlisted_messages), "specific unlisted request missed lookup policy")
    assert_true(any("No curated registry source matched" in message.get("content", "") for message in unlisted_messages), "unlisted request missed official-only fallback policy")
    assert_true(not any(message.get("content") == llm.OFFICIAL_LOOKUP_POLICY for message in other_messages), "official rule leaked to an unsupported provider")


def test_unlisted_provider_urls_are_downgraded_not_hidden():
    body = {
        "output": [
            {"type": "web_search_call", "status": "completed", "url": "https://forum.example.test/thread"},
            {"type": "message", "content": [{"type": "output_text", "text": "unsafe external conclusion"}]},
        ]
    }
    reply = llm.append_web_search_sources("unsafe external conclusion", body, {"asus.com"})
    assert_true("forum.example.test" in reply, "unlisted provider result was hidden instead of disclosed")
    assert_true("unsafe external conclusion" in reply, "answer text was incorrectly discarded")
    assert_true("\u672a\u5217\u5165\u4f18\u5148\u76ee\u5f55" in reply, "unlisted result was not downgraded")


def test_preferred_provider_urls_receive_an_official_priority_label():
    body = {
        "output": [
            {"type": "web_search_call", "status": "completed", "url": "https://www.asus.com/support/"},
            {"type": "message", "content": [{"type": "output_text", "text": "preferred source answer"}]},
        ]
    }
    reply = llm.append_web_search_sources("preferred source answer", body, {"asus.com"})
    assert_true("\u4f18\u5148\u5b98\u65b9\u6765\u6e90" in reply, "preferred official URL was not labelled")
    assert_true("\u672a\u5217\u5165\u4f18\u5148\u76ee\u5f55" not in reply, "preferred official URL was downgraded")


def test_lookup_is_server_decided_and_has_no_user_control():
    static_root = os.path.join(ROOT, "backend", "static")
    with open(os.path.join(static_root, "index.html"), encoding="utf-8") as source_file:
        html = source_file.read()
    with open(os.path.join(static_root, "app.js"), encoding="utf-8") as source_file:
        app = source_file.read()
    with open(os.path.join(static_root, "style.css"), encoding="utf-8") as source_file:
        css = source_file.read()
    with open(os.path.join(ROOT, "backend", "app", "main.py"), encoding="utf-8") as source_file:
        main = source_file.read()
    with open(os.path.join(ROOT, "backend", "app", "service.py"), encoding="utf-8") as source_file:
        service = source_file.read()

    assert_true("webSearchBtn" not in html and "web-search-btn" not in html, "user lookup button remains in composer")
    assert_true("webSearch" not in app, "client can still request lookup")
    assert_true("webSearch" not in main and "platform_web_search" not in main, "chat API still exposes user lookup state")
    assert_true('"model . img send"' in css and '"input img send"' in css, "composer grid did not close after removing lookup control")


TESTS = [
    ("W01", "official lookup gate accepts only DeepSeek V4 Flash", test_official_gate_is_narrow),
    ("W02", "server enables the tool without forcing a search", test_payload_makes_lookup_available_without_forcing_it),
    ("W03", "actual lookup uses official Responses and preserves sources", test_actual_lookup_uses_official_responses_and_discloses_sources),
    ("W04", "ordinary answer has no lookup banner", test_normal_answer_has_no_lookup_disclosure_when_model_did_not_search),
    ("W05", "non-official provider is rejected before network access", test_non_official_provider_fails_before_network_when_lookup_is_requested_internally),
    ("W06", "lookup prioritizes registry but allows a concrete unlisted manual request", test_service_prioritizes_registry_without_turning_it_into_a_wall),
    ("W07", "lookup is server-decided and the composer has no user switch", test_lookup_is_server_decided_and_has_no_user_control),
    ("W08", "unlisted provider URLs are disclosed as downgraded leads", test_unlisted_provider_urls_are_downgraded_not_hidden),
    ("W09", "preferred provider URLs retain an official-priority label", test_preferred_provider_urls_receive_an_official_priority_label),
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
    parser = __import__("argparse").ArgumentParser(description="Automatic official-lookup regression suite")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = run_tests()
    if args.json:
        print(json.dumps({"suite": "websearch", "results": results}, ensure_ascii=False))
    else:
        for result in results:
            suffix = f": {result.get('detail')}" if result.get("detail") else ""
            print(f"[{result['id']}] {result['name']}: {result['status']}{suffix}")
    raise SystemExit(0 if all(result["status"] == "PASS" for result in results) else 1)


if __name__ == "__main__":
    main()
