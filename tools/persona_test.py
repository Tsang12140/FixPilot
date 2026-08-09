"""
FixPilot 人设渐进式对话测试引擎（动态应答版）

核心思路：
  - scenarios.py 存的是"故障真相"，不是对话剧本
  - 陪练 AI（tutor LLM）扮演用户，依据故障真相 + 人设风格，动态回答 FixPilot 的提问
  - FixPilot 的提问不可预测，所以用户的回答也由陪练 AI 实时生成
  - 人设只影响"怎么说"，不改变事实

流程：
  1. 创建对话 -> 发 initial_complaint
  2. 收到 FixPilot 回复 -> 调陪练 AI 生成用户下一句（可附 [IMG:path] 图片 / [SOLVED] 标记）
  3. 把用户回答发给 FixPilot -> 循环，直到 [SOLVED] 或达到最大轮次
  4. 评分：检查 FixPilot 是否查对方向（key_evidence 关键词命中）
  5. 记录发现的 bug（空回复 / 500 / 图片 OCR 失败等）

用法:
  python tools/persona_test.py --base http://127.0.0.1:8000 --code 4CDB97
  python tools/persona_test.py --base http://127.0.0.1:8000 --code 4CDB97 --scenario A01
  python tools/persona_test.py --base http://127.0.0.1:8000 --admin-user <configured-admin> --admin-pass <configured-password> --persona A

陪练 LLM 默认读 backend/.env（DEEPSEEK_API_KEY/BASE_URL/MODEL），
也可用 --tutor-key/--tutor-base/--tutor-model 覆盖。
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime

import requests

# 同目录导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenarios import PERSONAS, SCENARIOS
from testkit import create_conversation, configure_profile, login_as_admin, login_with_code, send_chat


# ============================================================
# 陪练 LLM 接入
# ============================================================

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)
ENV_PATH = os.path.join(ROOT_DIR, "backend", ".env")


def _parse_env(path):
    """简单解析 .env，返回 dict（不依赖 python-dotenv）。"""
    data = {}
    if not os.path.isfile(path):
        return data
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data


def load_tutor_config(args):
    """读 backend/.env 作为陪练 LLM 默认配置，CLI 参数可覆盖。"""
    env = _parse_env(ENV_PATH)
    key = args.tutor_key or env.get("DEEPSEEK_API_KEY", "")
    base = args.tutor_base or env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = args.tutor_model or env.get("DEEPSEEK_MODEL", "deepseek-chat")

    base = (base or "").rstrip("/")
    is_ark = "ark.cn-beijing.volces.com" in base.lower()

    # 统一到 chat completions 端点
    if base.endswith("/responses"):
        base = base[: -len("/responses")]
    if base.endswith("/chat/completions"):
        url = base
    else:
        url = base + "/chat/completions"

    # deepseek 官方 API 没有 deepseek-v4-flash，陪练用 deepseek-chat 即可
    if not is_ark and model.startswith("deepseek-v4"):
        model = "deepseek-chat"

    if not key:
        raise RuntimeError(
            "陪练 LLM 缺少 API Key：在 backend/.env 配 DEEPSEEK_API_KEY，或用 --tutor-key 传入。"
        )
    return {"url": url, "key": key, "model": model, "is_ark": is_ark}


def _forced_image_path(facts, fixpilot_reply, sent_images, round_number=None):
    """Return the next scenario image when FixPilot asks for it or it is due."""
    reply = (fixpilot_reply or "").lower()
    candidates = []
    for image in facts.get("images", []):
        path = image.get("path", "")
        if not path or path in sent_images:
            continue
        candidates.append(image)
        triggers = image.get("send_when_asked_terms") or []
        if any(str(term).lower() in reply for term in triggers):
            return path
    if round_number is not None:
        for image in candidates:
            due_round = image.get("must_send_by_round")
            if isinstance(due_round, int) and round_number >= due_round:
                return image["path"]
    return None


def tutor_respond(cfg, persona, facts, history, fixpilot_reply, sent_images=None, round_number=None):
    """调用陪练 AI，返回 (user_text, image_path, solved)。

    history: [(role, text), ...] 截至本轮的对话（不含本轮 FixPilot 回复）
    fixpilot_reply: FixPilot 本轮回复（最新一条）
    """
    # Image coverage is a test invariant, not a behavior we leave to the tutor
    # model. Scenario records supply the available evidence and trigger terms.
    if sent_images is None:
        sent_images = set()
    forced_image = _forced_image_path(facts, fixpilot_reply, sent_images, round_number)

    # 拼对话历史给陪练看
    hist_text = ""
    for role, text in history:
        speaker = "FixPilot" if role == "assistant" else "你"
        hist_text += f"{speaker}: {text}\n"

    facts_block = json.dumps(facts, ensure_ascii=False, indent=2)

    # 可发图片清单
    img_list = "\n".join(
        f"- [IMG:{im['path']}]  说明: {im['shows']}  发送时机: {im['send_when']}"
        for im in facts.get("images", [])
    ) or "（本次无可用图片）"

    system_prompt = (
        "你在扮演一个真实用户，正在向 FixPilot（电脑故障排查 AI）描述并解决自己的电脑问题。"
        "你只能依据下面这份「你知道的真实情况」来回答，不要编造任何不在其中的细节。\n\n"
        f"【你知道的真实情况（facts）】\n{facts_block}\n\n"
        f"【你的表达风格】{persona['tutor_style']}\n\n"
        "【对话规则】\n"
        "1. 只回答 FixPilot 刚才问的那一个问题，不要主动透露还没被问到的信息（渐进式披露）。"
        "FixPilot 没问到的症状/硬件/时间线/操作结果，不要主动交代。\n"
        "2. 如果 FixPilot 给了编号选项（1./2./3.），选出最符合你情况的一项，"
        "用自己的话复述那项内容即可，不要报编号。\n"
        "3. 你不知道根因，不要主动说「是不是内存松了」这种结论；你只知道现象和做过的操作。\n"
        "4. 如果 FixPilot 让你做一个操作，按 facts.action_outcomes 里最匹配那条的 result "
        "描述你做完后看到/发生了什么；若没有匹配条目，按你的 capabilities 如实回答"
        "（能做到就描述结果，做不到就说不敢/不会/没有工具）。\n"
        "5. 当你做完一个标记了 \"solves\": true 的操作并报告了它的 result，"
        "说明问题已经解决，在回复最后另起一行写 [SOLVED]。\n"
        "   另外：如果问题已经明显好转/解决（你不卡了/能开机了/不蓝了/能上网了等），"
        "即使没匹配到 solves 标记的操作，也要在回复末尾加 [SOLVED] 结束对话。\n"
        "   如果 FixPilot 已结束指导、双方在道别，不要反复说再见，直接 [SOLVED] 收尾。\n"
        "6. 需要发图片时，在回复最后另起一行写 [IMG:图片文件名]（一次最多一张）。\n"
        "   可用图片清单：\n" + img_list + "\n"
        "   只有在 FixPilot 主动问到、或你正在描述现象确实需要图时才发；不要重复发同一张。\n"
        "   发图片时，文字里不要重复图片里能直接看到的代码/报错文字（如蓝屏代码、错误码），\n"
        "   只描述图片是什么（如'我拍了蓝屏的图''这是任务管理器'），让 FixPilot 自己看图识别。\n"
        "7. 回复简短（一般一两句），像真人聊天，不要分点罗列，不要用 emoji 和圆点符号。\n"
        "8. 只输出用户说的话本身（必要时附 [IMG:...] 或 [SOLVED] 标记），不要加引号、不要解释你在扮演谁。\n"
    )

    user_prompt = (
        f"【到目前为止的对话】\n{hist_text}\n"
        f"FixPilot 刚才说：\n{fixpilot_reply}\n\n"
        "请用第一人称，以这个用户的口吻回复 FixPilot："
    )

    headers = {
        "Authorization": f"Bearer {cfg['key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "temperature": 0.9,
        "max_tokens": 300,
    }
    # Ark 对多余字段宽容，保留通用参数即可

    try:
        r = requests.post(cfg["url"], headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        text = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if not text:
            raise RuntimeError("陪练 AI 返回空内容")
    except Exception as e:
        # Keep a requested image deterministic even if the tutor model is unavailable.
        if forced_image:
            return "我把截图发上来了。", forced_image, False
        # 陪练失败，回退一个最小回复，避免测试中断
        return f"（陪练 AI 故障: {e}）", None, False

    # 解析 [IMG:path] 和 [SOLVED]
    solved = "[SOLVED]" in text
    text = text.replace("[SOLVED]", "").strip()

    img_path = None
    m = re.search(r"\[IMG:([^\]]+)\]", text)
    if m:
        img_path = m.group(1).strip()
        text = (text[: m.start()] + text[m.end():]).strip()

    if forced_image:
        # The tutor may omit the marker. Keep its ordinary answer, but ensure the
        # relevant screenshot is part of this turn so the OCR path is exercised.
        img_path = forced_image
        if "图" not in text and "截图" not in text:
            text = (text + " 我把截图一并发上来。").strip()

    return text or "你看看", img_path, solved


# ============================================================
# FixPilot 后端交互
# ============================================================

# ============================================================
# FixPilot backend interaction: shared auth, profile setup and SSE parsing via testkit.
# ============================================================

def send_message(base, token, text, conv_id, image_path=None):
    """Send through the shared transport, preserving this suite's image root."""
    return send_chat(base, token, text, conv_id, image_path, assets_dir=TOOLS_DIR)


def grade_scenario(scenario, fixpilot_replies):
    """Grade broad clues separately from diagnosis-specific direction evidence."""
    grading = scenario["grading"]
    evidence = grading.get("key_evidence", [])
    all_text = " ".join(fixpilot_replies).lower()
    hits = [kw for kw in evidence if kw.lower() in all_text]

    # Broad words such as "administrator", "driver", or an error code are often
    # repeated from the user's prompt. They are useful observations, not proof
    # that FixPilot selected the scenario's distinguishing diagnosis direction.
    groups = grading.get("direction_evidence_groups") or []
    group_hits = [
        [term for term in group if term.lower() in all_text]
        for group in groups
    ]
    diagnosis_correct = bool(groups) and all(group for group in group_hits)
    return {
        "key_evidence": evidence,
        "hits": hits,
        "direction_evidence_groups": groups,
        "direction_group_hits": group_hits,
        "diagnosis_correct": diagnosis_correct,
    }

def run_scenario(base, token, tutor_cfg, scenario, max_rounds=18, verbose=True, profile_mode="explicit", response_style=None):
    """跑一个场景：陪练 AI 动态应答 FixPilot。"""
    persona = PERSONAS[scenario["persona"]]
    facts = scenario["facts"]
    configured_profile = None
    selected_style = response_style or persona["style"]
    try:
        if profile_mode == "explicit":
            configured_profile = configure_profile(
                base, token, persona["tech_level"], selected_style
            )
        else:
            configured_profile = configure_profile(base, token, "unknown", "normal")
    except Exception as exc:
        return {
            "scenario_id": scenario["id"], "persona": scenario["persona"],
            "title": scenario["title"], "root_cause": scenario["grading"]["root_cause"],
            "profile_mode": profile_mode, "configured_profile": None,
            "rounds_completed": 0, "solved": False, "diagnosis_correct": False,
            "evidence_hits": [], "conv_id": None, "rounds_log": [],
            "bugs": [{"round": 0, "scenario": scenario["id"], "type": "profile_setup_error", "detail": str(exc)}],
        }
    conv_id = create_conversation(base, token, title=f"test-{scenario['id']}")
    rounds_log = []
    bugs = []
    history = []  # [(role, text)] 给陪练看
    fixpilot_replies = []

    if verbose:
        print(f"\n{'='*70}")
        print(f"场景 {scenario['id']} | {persona['label']} | {scenario['title']}")
        print(f"真相: {scenario['grading']['root_cause']}")
        print(f"{'='*70}")

    # 第 1 轮：发初始主诉
    first_text = facts["initial_complaint"]
    first_img = None
    # 初始主诉一般不带图，除非用户上来就发图（这里不发）
    reply, status, extra = send_message(base, token, first_text, conv_id, first_img)
    rounds_log.append({
        "round": 1, "user": first_text, "image": None,
        "ai_reply": reply, "status": status, "extra": extra,
    })
    history.append(("user", first_text))
    if reply:
        history.append(("assistant", reply))
        fixpilot_replies.append(reply)
    _record_bugs(bugs, 1, status, extra, reply, scenario, conv_id)
    if verbose:
        print(f"  [R1] 用户: {first_text}")
        print(f"  [R1] AI: {reply[:120]}{'...' if len(reply)>120 else ''}")

    # 第 2~N 轮：陪练 AI 应答
    solved = False
    sent_images = set()
    for rnd in range(2, max_rounds + 1):
        if not reply:
            # 上一轮 AI 回复为空，无法继续问诊
            if verbose:
                print(f"  [R{rnd}] 上一轮 AI 回复为空，停止")
            break

        time.sleep(0.8)
        user_text, img_path, just_solved = tutor_respond(
            tutor_cfg, persona, facts, history, reply, sent_images, rnd
        )

        full_user = user_text
        reply, status, extra = send_message(base, token, user_text, conv_id, img_path)
        if img_path:
            sent_images.add(img_path)

        rounds_log.append({
            "round": rnd, "user": full_user, "image": img_path,
            "ai_reply": reply, "status": status, "extra": extra,
        })
        history.append(("user", full_user))
        if reply:
            history.append(("assistant", reply))
            fixpilot_replies.append(reply)
        _record_bugs(bugs, rnd, status, extra, reply, scenario, conv_id, img_path, user_text)

        if verbose:
            print(f"  [R{rnd}] 用户: {full_user}" + (f"  [图: {img_path}]" if img_path else ""))
            print(f"  [R{rnd}] AI: {reply[:120]}{'...' if len(reply)>120 else ''}")

        if just_solved:
            solved = True
            if verbose:
                print(f"  [R{rnd}] 陪练标记 [SOLVED]，问题解决，结束")
            break

        # 兜底：如果陪练连续说"不知道/不会"且 AI 重复，避免死循环
        if rnd >= 6 and len(set(r["user"] for r in rounds_log[-3:])) == 1:
            if verbose:
                print(f"  [R{rnd}] 检测到用户回复重复，提前结束")
            break

        # 兜底：道别循环（双方已无新诊断内容，反复拜拜）视为已收尾
        if rnd >= 6:
            bye_re = re.compile(r"拜拜|再见|回见|走了|忙去|散了|去忙|先这样|那我走")
            recent = rounds_log[-3:]
            if all(bye_re.search(r["user"]) and len(r["user"]) < 40 for r in recent):
                solved = True
                if verbose:
                    print(f"  [R{rnd}] 检测到道别循环，视为已收尾结束")
                break

    grading = grade_scenario(scenario, fixpilot_replies)

    return {
        "scenario_id": scenario["id"],
        "persona": scenario["persona"],
        "title": scenario["title"],
        "root_cause": scenario["grading"]["root_cause"],
        "profile_mode": profile_mode,
        "configured_profile": configured_profile,
        "rounds_completed": len(rounds_log),
        "solved": solved,
        "diagnosis_correct": grading["diagnosis_correct"],
        "evidence_hits": grading["hits"],
        "conv_id": conv_id,
        "rounds_log": rounds_log,
        "bugs": bugs,
    }


def _record_bugs(bugs, rnd, status, extra, reply, scenario, conv_id, img_path=None, user_text=""):
    """记录测试中发现的 bug。"""
    # 1. HTTP 非 200 / 500
    if status != 200:
        bugs.append({
            "round": rnd, "conv_id": conv_id, "scenario": scenario["id"],
            "type": "http_error", "status": status,
            "detail": (extra.get("error") or "")[:300] if isinstance(extra, dict) else str(extra),
            "user_said": user_text, "image": img_path,
        })
        return
    # 1.5 HTTP succeeded but the backend emitted an SSE error event. Keep it
    # distinct from an HTTP failure so provider diagnosis stays truthful.
    if isinstance(extra, dict) and extra.get("stream_error"):
        bugs.append({
            "round": rnd, "conv_id": conv_id, "scenario": scenario["id"],
            "type": "stream_error", "status": status,
            "detail": (extra.get("error") or "")[:300],
            "user_said": user_text, "image": img_path,
        })
        return
    # 2. 空回复
    if not reply or not reply.strip():
        bugs.append({
            "round": rnd, "conv_id": conv_id, "scenario": scenario["id"],
            "type": "empty_reply", "detail": "FixPilot 返回空回复",
            "user_said": user_text, "image": img_path,
        })
        return
    # 3. 图片发送了，但 FixPilot 说看不到图/收不到/无法识别（OCR 失败特征）
    if img_path:
        cant_see = re.search(
            r"看不到|看不了|没法看|无法看|不能看|收不到|收不了|接收不到|没法收到|"
            r"打不开|识别不到|无法识别|识别不了|没法识别|没收到图|没发图|没收到|"
            r"只能收文字|只能文字|走文字路线|变成.{0,6}看不见|真的看不了|真的收不到",
            reply,
        )
        if cant_see:
            bugs.append({
                "round": rnd, "conv_id": conv_id, "scenario": scenario["id"],
                "type": "image_not_seen", "image": img_path,
                "detail": f"用户发了图片 {img_path}，但 FixPilot 回复: {reply[:200]}",
                "user_said": user_text,
            })
    # 4. 图片文件缺失
    if isinstance(extra, dict) and extra.get("image_missing"):
        bugs.append({
            "round": rnd, "conv_id": conv_id, "scenario": scenario["id"],
            "type": "image_file_missing", "image": extra["image_missing"],
            "detail": f"测试图片文件不存在: {extra['image_missing']}",
        })


# ============================================================
# 汇总
# ============================================================

def run_persona_tests(base, token, tutor_cfg, persona_filter=None, scenario_filter=None,
                     max_rounds=18, verbose=True, profile_mode="explicit", response_style=None):
    results = []
    for sc in SCENARIOS:
        if persona_filter and sc["persona"] != persona_filter:
            continue
        if scenario_filter and sc["id"] != scenario_filter:
            continue
        result = run_scenario(base, token, tutor_cfg, sc, max_rounds, verbose, profile_mode, response_style)
        results.append(result)
        time.sleep(2)
    return results


def summarize(results):
    """打印汇总并返回总 bug 列表。"""
    print(f"\n{'='*70}")
    print(f"测试汇总")
    print(f"{'='*70}")
    total_bugs = []
    for r in results:
        diag = "查对" if r["diagnosis_correct"] else "未查对"
        sol = "已解决" if r["solved"] else "未解决"
        print(f"  {r['scenario_id']} | {r['persona']:12s} | {r['rounds_completed']:2d}轮 | "
              f"{diag} | {sol} | {r['title']}")
        if r["evidence_hits"]:
            print(f"         证据命中: {', '.join(r['evidence_hits'])}")
        for b in r["bugs"]:
            total_bugs.append(b)
            print(f"         [BUG] R{b['round']} {b['type']}: {b.get('detail','')[:120]}")
    print(f"{'='*70}")
    print(f"场景: {len(results)} | 总 bug: {len(total_bugs)}")
    return total_bugs


def main():
    parser = argparse.ArgumentParser(description="FixPilot 人设渐进式对话测试（动态应答版）")
    parser.add_argument("--base", default="http://127.0.0.1:8000", help="FixPilot 服务地址")
    parser.add_argument("--code", help="邀请码")
    parser.add_argument("--admin-user", help="管理员用户名")
    parser.add_argument("--admin-pass", help="管理员密码")
    parser.add_argument("--persona", choices=["A", "B", "C"], help="只跑指定人设")
    parser.add_argument("--scenario", help="只跑指定场景 ID (如 A01)")
    parser.add_argument("--max-rounds", type=int, default=18, help="单场景最大对话轮次")
    parser.add_argument("--profile-mode", choices=["explicit", "unknown"], default="explicit", help="explicit=manual level; unknown=inference path")
    parser.add_argument("--response-style", choices=["normal", "roast", "concise"], default=None, help="override persona style to test the level/style axes separately")
    parser.add_argument("--output", default=None, help="结果输出到 JSON 文件")
    # 陪练 LLM 配置
    parser.add_argument("--tutor-key", help="陪练 AI 的 API Key（默认读 backend/.env）")
    parser.add_argument("--tutor-base", help="陪练 AI 的 base url（默认读 backend/.env）")
    parser.add_argument("--tutor-model", help="陪练 AI 的模型名（默认读 backend/.env）")
    args = parser.parse_args()

    # 登录 FixPilot
    if args.admin_user and args.admin_pass:
        print(f"管理员登录: {args.admin_user}")
        token = login_as_admin(args.base, args.admin_user, args.admin_pass)
    elif args.code:
        print(f"邀请码登录: {args.code}")
        token = login_with_code(args.base, args.code)
    else:
        print("需要 --code 或 --admin-user/--admin-pass")
        sys.exit(1)

    # 陪练 LLM 配置
    try:
        tutor_cfg = load_tutor_config(args)
    except RuntimeError as e:
        print(f"陪练 LLM 配置失败: {e}")
        sys.exit(2)
    print(f"陪练 LLM: {tutor_cfg['model']} @ {tutor_cfg['url']}")
    print(f"登录成功，开始人设测试...\n")

    results = run_persona_tests(
        args.base, token, tutor_cfg,
        persona_filter=args.persona, scenario_filter=args.scenario,
        max_rounds=args.max_rounds, verbose=True, profile_mode=args.profile_mode, response_style=args.response_style,
    )

    total_bugs = summarize(results)

    if args.output:
        payload = {
            "ran_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tutor_model": tutor_cfg["model"],
            "results": results,
            "bugs": total_bugs,
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到 {args.output}")

    has_issues = bool(total_bugs) or any(not r["diagnosis_correct"] for r in results)
    sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
