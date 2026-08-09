"""FixPilot modular product-test runner.

Project suites own their own truth and assertions. This runner only coordinates
authentication, selection, artifacts, and a truthful exit code.
"""
import argparse
import json
import os
import sys
import subprocess
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from injection_test import run_tests as run_injection_tests
from persona_test import load_tutor_config, run_persona_tests
from safety_test import run_tests as run_safety_tests
from testkit import login_as_admin, login_with_code

ALL_SUITES = ("renderer", "transport", "websearch", "sources", "injection", "safety", "persona")


def summarize_status(items):
    summary = {"PASS": 0, "FAIL": 0, "ERROR": 0, "REVIEW": 0}
    for item in items:
        status = item.get("status")
        if status in summary:
            summary[status] += 1
    return summary


def persona_statuses(results):
    """Map persona results to statuses without hiding bugs as a successful run."""
    mapped = []
    for result in results:
        bugs = result.get("bugs") or []
        status = "PASS"
        if any(
            bug.get("type") in {"http_error", "stream_error", "empty_reply", "profile_setup_error"}
            for bug in bugs
        ):
            status = "ERROR"
        elif bugs or not result.get("diagnosis_correct"):
            status = "FAIL"
        mapped.append({"id": result.get("scenario_id"), "status": status})
    return mapped


def parse_suites(raw):
    requested = tuple(item.strip() for item in raw.split(",") if item.strip())
    invalid = sorted(set(requested) - set(ALL_SUITES))
    if invalid:
        raise ValueError(f"unknown suite(s): {', '.join(invalid)}")
    return requested or ALL_SUITES


def run_local_json_suite(script_name, suite_name, executable):
    """Run a no-network tool that writes the common JSON result shape."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
    try:
        completed = subprocess.run(
            [executable, script, "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        return [{"id": f"{suite_name[:1].upper()}00", "name": f"{suite_name} runner", "status": "ERROR", "detail": f"{executable} is not installed"}]
    except subprocess.TimeoutExpired:
        return [{"id": f"{suite_name[:1].upper()}00", "name": f"{suite_name} runner", "status": "ERROR", "detail": f"{suite_name} test timed out"}]

    try:
        payload = json.loads(completed.stdout or "{}")
        results = payload.get("results")
        if not isinstance(results, list):
            raise ValueError("missing results")
    except (json.JSONDecodeError, ValueError) as exc:
        detail = (completed.stderr or completed.stdout or str(exc)).strip()[:600]
        return [{"id": f"{suite_name[:1].upper()}00", "name": f"{suite_name} runner", "status": "ERROR", "detail": detail or "invalid test output"}]

    if completed.returncode and all(item.get("status") == "PASS" for item in results):
        results.append({"id": f"{suite_name[:1].upper()}00", "name": f"{suite_name} runner", "status": "ERROR", "detail": "test exited non-zero"})
    return results


def run_renderer_tests():
    """Run DOM-free frontend answer-renderer checks without model calls."""
    return run_local_json_suite("renderer_test.js", "renderer", "node")


def run_transport_tests():
    """Run no-network retry and safety-preflight guardrail checks."""
    return run_local_json_suite("transport_test.py", "transport", sys.executable)

def run_websearch_tests():
    """Run no-network official DeepSeek web-search boundary checks."""
    return run_local_json_suite("web_search_test.py", "websearch", sys.executable)

def run_sources_tests():
    """Run no-network official-source registry integrity checks."""
    return run_local_json_suite("official_sources_test.py", "sources", sys.executable)

def main():
    parser = argparse.ArgumentParser(description="FixPilot 模块化产品回归测试")
    parser.add_argument("--base", default="http://127.0.0.1:8000", help="FixPilot 服务地址")
    parser.add_argument("--code", help="邀请码登录")
    parser.add_argument("--admin-user", help="管理员用户名")
    parser.add_argument("--admin-pass", help="管理员密码")
    parser.add_argument("--suites", default=",".join(ALL_SUITES), help="以逗号分隔：renderer,transport,websearch,injection,safety,persona")
    parser.add_argument("--skip-renderer", action="store_true", help="跳过 renderer")
    parser.add_argument("--skip-transport", action="store_true", help="跳过 transport")
    parser.add_argument("--skip-websearch", action="store_true", help="skip websearch")
    parser.add_argument("--skip-injection", action="store_true", help="兼容旧命令：跳过 injection")
    parser.add_argument("--skip-safety", action="store_true", help="跳过 safety")
    parser.add_argument("--skip-persona", action="store_true", help="兼容旧命令：跳过 persona")
    parser.add_argument("--persona", choices=["A", "B", "C"], help="只跑指定人设")
    parser.add_argument("--profile-mode", choices=["explicit", "unknown"], default="explicit", help="explicit=manual selection; unknown=inference path")
    parser.add_argument("--response-style", choices=["normal", "roast", "concise"], default=None, help="override persona style for axis-isolated coverage")
    parser.add_argument("--max-rounds", type=int, default=18, help="每个人设场景最多轮数")
    parser.add_argument("--output-dir", default="reports/test-runs", help="JSON result directory; defaults to local evidence")
    parser.add_argument("--tutor-key", help="陪练 AI API key；不会写入结果文件")
    parser.add_argument("--tutor-base", help="陪练 AI base URL")
    parser.add_argument("--tutor-model", help="陪练 AI 模型")
    args = parser.parse_args()

    try:
        suites = set(parse_suites(args.suites))
    except ValueError as exc:
        parser.error(str(exc))
    for suite, skip in (("renderer", args.skip_renderer), ("transport", args.skip_transport), ("websearch", args.skip_websearch), ("sources", False), ("injection", args.skip_injection), ("safety", args.skip_safety), ("persona", args.skip_persona)):
        if skip:
            suites.discard(suite)
    if not suites:
        parser.error("没有选择要运行的测试模块")

    token = None
    needs_auth = bool(suites & {"injection", "safety", "persona"})
    if needs_auth:
        if args.admin_user and args.admin_pass:
            token = login_as_admin(args.base, args.admin_user, args.admin_pass)
        elif args.code:
            token = login_with_code(args.base, args.code)
        else:
            parser.error("credentials are required for injection, safety, or persona")

    all_results = {
        "schema_version": 1,
        "project": "FixPilot",
        "started_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "base_url": args.base,
        "selected_suites": sorted(suites),
        "profile_mode": args.profile_mode,
        "response_style": args.response_style,
        "results": {},
    }

    if "renderer" in suites:
        print("\n# renderer: answer rendering integrity")
        all_results["results"]["renderer"] = run_renderer_tests()
    if "transport" in suites:
        print("\n# transport: retry and safety guardrails")
        all_results["results"]["transport"] = run_transport_tests()
    if "websearch" in suites:
        print("\n# websearch: official DeepSeek V4 Flash boundary")
        all_results["results"]["websearch"] = run_websearch_tests()
    if "sources" in suites:
        print("\n# sources: official-reference registry integrity")
        all_results["results"]["sources"] = run_sources_tests()
    if "injection" in suites:
        print("\n# injection：提示词注入边界")
        all_results["results"]["injection"] = run_injection_tests(args.base, token)
    if "safety" in suites:
        print("\n# safety：风险提示与停止指导")
        all_results["results"]["safety"] = run_safety_tests(args.base, token)
    if "persona" in suites:
        print("\n# persona：动态用户人设与故障诊断")
        tutor_cfg = load_tutor_config(args)
        print(f"陪练模型：{tutor_cfg['model']} @ {tutor_cfg['url']}")
        all_results["results"]["persona"] = run_persona_tests(
            args.base, token, tutor_cfg, persona_filter=args.persona,
            max_rounds=args.max_rounds, profile_mode=args.profile_mode, response_style=args.response_style,
        )

    all_results["finished_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    all_results["summary"] = {}
    failed = False
    print("\n" + "=" * 64 + "\n测试摘要\n" + "=" * 64)
    for suite, results in all_results["results"].items():
        statuses = persona_statuses(results) if suite == "persona" else results
        summary = summarize_status(statuses)
        all_results["summary"][suite] = summary
        failed = failed or any(summary[key] for key in ("FAIL", "ERROR", "REVIEW"))
        print(f"{suite}: PASS {summary['PASS']} / FAIL {summary['FAIL']} / ERROR {summary['ERROR']} / REVIEW {summary['REVIEW']}")

    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
        output_path = os.path.join(args.output_dir, "test-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".json")
        with open(output_path, "w", encoding="utf-8") as result_file:
            json.dump(all_results, result_file, ensure_ascii=False, indent=2)
        print(f"\n结果已保存：{output_path}")

    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
