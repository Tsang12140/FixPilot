"""
FixPilot 一键跑全部测试
先跑注入测试，再跑人设测试，最后汇总输出报告
用法: python tools/run_all.py --base http://127.0.0.1:8000 --code 4CDB97
"""
import argparse
import json
import sys
import os
from datetime import datetime

# 同目录导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from injection_test import login_with_code, login_as_admin, run_tests as run_injection_tests
from persona_test import run_persona_tests, load_tutor_config


def main():
    parser = argparse.ArgumentParser(description="FixPilot 一键跑全部测试")
    parser.add_argument("--base", default="http://127.0.0.1:8000", help="服务地址")
    parser.add_argument("--code", help="邀请码")
    parser.add_argument("--admin-user", help="管理员用户名")
    parser.add_argument("--admin-pass", help="管理员密码")
    parser.add_argument("--skip-injection", action="store_true", help="跳过注入测试")
    parser.add_argument("--skip-persona", action="store_true", help="跳过人设测试")
    parser.add_argument("--persona", choices=["beginner", "intermediate", "advanced"], help="只跑指定人设")
    parser.add_argument("--output-dir", default=None, help="结果输出目录")
    parser.add_argument("--tutor-key", help="陪练 AI 的 API Key（默认读 backend/.env）")
    parser.add_argument("--tutor-base", help="陪练 AI 的 base url（默认读 backend/.env）")
    parser.add_argument("--tutor-model", help="陪练 AI 的模型名（默认读 backend/.env）")
    args = parser.parse_args()

    # 登录
    if args.admin_user and args.admin_pass:
        print(f"管理员登录: {args.admin_user}")
        token = login_as_admin(args.base, args.admin_user, args.admin_pass)
    elif args.code:
        print(f"邀请码登录: {args.code}")
        token = login_with_code(args.base, args.code)
    else:
        print("需要 --code 或 --admin-user/--admin-pass")
        sys.exit(1)

    print(f"登录成功\n")
    all_results = {}
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    # 1. 注入测试
    if not args.skip_injection:
        print(f"\n{'#'*60}")
        print(f"# Phase 1: 注入边界测试 (12 类)")
        print(f"{'#'*60}\n")
        injection_results = run_injection_tests(args.base, token)
        all_results["injection"] = injection_results

    # 2. 人设测试
    if not args.skip_persona:
        print(f"\n{'#'*60}")
        print(f"# Phase 2: 人设渐进式对话测试")
        print(f"{'#'*60}\n")
        tutor_cfg = load_tutor_config(args)
        print(f"陪练 LLM: {tutor_cfg['model']} @ {tutor_cfg['url']}\n")
        persona_results = run_persona_tests(args.base, token, tutor_cfg, persona_filter=args.persona)
        all_results["persona"] = persona_results

    # 3. 汇总
    print(f"\n{'='*60}")
    print(f"全部测试完成")
    print(f"{'='*60}")

    if all_results.get("injection"):
        inj = all_results["injection"]
        passed = sum(1 for r in inj if r["status"] == "PASS")
        failed = sum(1 for r in inj if r["status"] == "FAIL")
        print(f"注入测试: {passed} PASS / {failed} FAIL / {len(inj)} 总计")

    if all_results.get("persona"):
        per = all_results["persona"]
        total_rounds = sum(r["rounds_completed"] for r in per)
        total_bugs = sum(len(r["bugs"]) for r in per)
        correct = sum(1 for r in per if r["diagnosis_correct"])
        solved = sum(1 for r in per if r["solved"])
        print(f"人设测试: {len(per)} 场景 / {total_rounds} 轮 / 查对{correct} / 解决{solved} / bug{total_bugs}")

    # 输出 JSON
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
        out_file = os.path.join(args.output_dir, f"test-{ts}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到 {out_file}")

    # 非 0 退出如果有问题
    has_failures = False
    if all_results.get("injection"):
        has_failures = any(r["status"] == "FAIL" for r in all_results["injection"])
    if all_results.get("persona"):
        has_failures = has_failures or any(r["bugs"] or not r["diagnosis_correct"] for r in all_results["persona"])
    sys.exit(1 if has_failures else 0)


if __name__ == "__main__":
    main()
