"""No-network regression checks for FixPilot transport and safety guardrails."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from app import llm, safety


class FakeStreamResponse:
    def __init__(self, lines):
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self):
        return None

    def iter_lines(self):
        yield from self.lines


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


def test_risk_preflight_classifier():
    assert_true(
        safety.infer_risk_level("\u6211\u51c6\u5907\u8fdb BIOS \u6539\u542f\u52a8\u548c\u5185\u5b58\u8bbe\u7f6e") == "high",
        "BIOS change was not classified as high risk",
    )
    assert_true(
        safety.infer_risk_level("\u6211\u60f3\u628a\u663e\u5361\u9a71\u52a8\u5f7b\u5e95\u5378\u6389\u518d\u88c5") == "medium",
        "driver uninstall/reinstall was not classified as medium risk",
    )
    assert_true(
        safety.infer_risk_level("BIOS \u662f\u4ec0\u4e48\uff1f") is None,
        "a read-only BIOS question was incorrectly classified as risky",
    )


def test_empty_reply_gets_one_safe_retry():
    original_stream = llm.httpx.stream
    original_post = llm.httpx.post
    original_sleep = llm.time.sleep
    posts = []

    def fake_stream(*args, **kwargs):
        return FakeStreamResponse([
            'data: {"choices":[{"delta":{"reasoning_content":"hidden"}}]}',
            "data: [DONE]",
        ])

    def fake_post(*args, **kwargs):
        posts.append(kwargs.get("json", {}))
        if len(posts) == 1:
            return FakeResponse({"choices": [{"message": {"content": ""}}]})
        return FakeResponse({"choices": [{"message": {"content": "retry answer"}}]})

    try:
        llm.httpx.stream = fake_stream
        llm.httpx.post = fake_post
        llm.time.sleep = lambda _seconds: None
        reply = "".join(llm.stream_chat(
            [{"role": "user", "content": "hello"}],
            api_key="test-key", base_url="https://example.test", model="test-model",
        ))
    finally:
        llm.httpx.stream = original_stream
        llm.httpx.post = original_post
        llm.time.sleep = original_sleep

    assert_true(reply == "retry answer", "the second completed attempt was not returned")
    assert_true(len(posts) == 2, "empty reply should use exactly one retry")
    assert_true(all(item.get("stream") is False for item in posts), "fallback attempts must be completed requests")


def test_visible_stream_never_retries():
    original_stream = llm.httpx.stream
    original_post = llm.httpx.post
    posts = []

    def fake_stream(*args, **kwargs):
        return FakeStreamResponse([
            'data: {"choices":[{"delta":{"content":"visible answer"}}]}',
            "data: [DONE]",
        ])

    def fake_post(*args, **kwargs):
        posts.append(kwargs)
        return FakeResponse({"choices": [{"message": {"content": "must not be used"}}]})

    try:
        llm.httpx.stream = fake_stream
        llm.httpx.post = fake_post
        reply = "".join(llm.stream_chat(
            [{"role": "user", "content": "hello"}],
            api_key="test-key", base_url="https://example.test", model="test-model",
        ))
    finally:
        llm.httpx.stream = original_stream
        llm.httpx.post = original_post

    assert_true(reply == "visible answer", "visible stream text was not preserved")
    assert_true(not posts, "a visible stream must not trigger a duplicate fallback")


TESTS = [
    ("T01", "risk preflight classifies BIOS and driver operations", test_risk_preflight_classifier),
    ("T02", "empty stream and empty fallback retry once", test_empty_reply_gets_one_safe_retry),
    ("T03", "visible stream never retries", test_visible_stream_never_retries),
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
    parser = argparse.ArgumentParser(description="FixPilot transport and guardrail regression tests")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = run_tests()
    failed = any(result["status"] != "PASS" for result in results)
    if args.json:
        print(json.dumps({"suite": "transport", "results": results}, ensure_ascii=False))
    else:
        for result in results:
            suffix = f" ({result.get('detail')})" if result.get("detail") else ""
            print(f"[{result['id']}] {result['name']}: {result['status']}{suffix}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()