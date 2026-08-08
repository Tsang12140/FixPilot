"""用户技术水平的本地证据提取与画像聚合。"""
import re
from typing import Dict, List


LEVELS = ("beginner", "intermediate", "advanced")


def _signal(valid: bool = False, level: str = "uncertain", strength: int = 0,
            evidence_types: List[str] = None, copy_risk: bool = False, reason: str = "") -> Dict:
    return {"profiling_valid": valid, "level_vote": level, "strength": strength,
            "evidence_type": evidence_types or [], "copy_risk": copy_risk, "reason": reason}


def classify_turn(text: str) -> Dict:
    """提取技术水平证据；不会因一个术语、命令或硬件直接判高手。"""
    raw = (text or "").strip()
    compact = re.sub(r"\s+", "", raw.lower())
    if not compact or re.fullmatch(r"(你好|嗨|在吗|谢谢|谢了|好的|嗯|ok|okk|？|\?)+", compact):
        return _signal(reason="问候、感谢或无实质信息")
    if "图片中未识别到文字" in raw and len(compact) < 28:
        return _signal(reason="图片没有提供可用于画像的文字")

    beginner_patterns = (
        r"bios.{0,4}(是|在哪|怎么进|不会)", r"安全模式.{0,5}(是|在哪|怎么进|不会)",
        r"设备管理器.{0,5}(在哪|怎么打开|不会)", r"驱动.{0,5}(是什么|在哪|怎么装)",
        r"(我|完全)?不太懂(电脑|这些|这个)?", r"不知道.{0,8}(在哪|怎么|什么意思)",
    )
    if any(re.search(pattern, compact) for pattern in beginner_patterns):
        return _signal(True, "beginner", 3, ["concept_understanding", "operation_independence"],
                       reason="用户明确表示不理解关键概念或不知道操作入口")
    if re.search(r"(点不到|找不到|看不懂).{0,10}(设置|选项|菜单|那个)", compact):
        return _signal(True, "beginner", 2, ["operation_independence"],
                       reason="用户需要把操作路径拆得更细")

    tech_terms = r"(bios|uefi|安全模式|设备管理器|事件查看器|蓝屏|minidump|dump|ddu|sfc|dism|驱动|注册表|nvme|ssd|内存|显卡|主板|bitlocker)"
    has_tech_term = bool(re.search(tech_terms, compact))
    has_self_action = bool(re.search(r"(我|已经|自己|刚刚).{0,8}(进|看|试|跑|换|卸|装|清|查|测|排)", compact))
    has_result = bool(re.search(r"(正常|不正常|没有|还是|复现|不复现|报错|识别|能进|进不去|没变化|恢复)", compact))
    has_reasoning = bool(re.search(r"(所以|因此|说明|排除|更像|怀疑|倾向|优先|缩小|对照|控制变量)", compact))
    has_comparison = bool(re.search(r"(安全模式.{0,12}(正常|不复现|没事)|换.{0,12}(还是|正常|没变化)|更新.{0,12}后.{0,10}(开始|出现)|只在.{0,10}(出现|复现)|另一(块|台).{0,15}(正常|没事))", compact))

    if has_self_action and has_result and (has_reasoning or has_comparison) and has_tech_term:
        evidence = ["operation_independence", "diagnostic_reasoning"]
        if has_comparison:
            evidence.append("controlled_comparison")
        return _signal(True, "advanced", 3, evidence,
                       reason="用户给出了独立操作结果，并用对照或因果判断缩小了故障方向")
    if has_self_action and has_result and has_tech_term:
        return _signal(True, "intermediate", 2, ["operation_independence", "technical_feedback"],
                       reason="用户能独立完成常见操作并反馈结果，但尚未形成稳定的对照判断")

    command_or_log = bool(re.search(r"(sfc/scannow|dism|0x[0-9a-f]+|\.sys|event\s*id|bugcheck|\b[a-z]+\.exe\b)", compact))
    if command_or_log and not (has_self_action or has_reasoning or has_result):
        return _signal(True, "intermediate", 1, ["technical_information"], True,
                       "用户只提供了命令、日志或模块名，可能来自教程或复制内容")
    if has_self_action and has_tech_term:
        return _signal(True, "intermediate", 1, ["operation_independence"],
                       reason="用户表明做过常见电脑操作")
    if re.search(r"(win(10|11)|windows|开机|蓝屏|黑屏|卡死|闪退).{0,30}(型号|版本|错误码|风扇|硬盘|内存|显卡)", compact):
        return _signal(True, "intermediate", 1, ["technical_information"],
                       reason="用户主动提供了对排障有区分度的系统或硬件信息")
    return _signal(reason="本轮对故障可能有用，但不足以判断操作深度")


def apply_signal(profile: Dict, signal: Dict) -> Dict:
    """按 v1 规则聚合证据。返回可直接写回数据库的画像。"""
    updated = dict(profile)
    if not signal.get("profiling_valid"):
        return updated
    vote, strength = signal.get("level_vote"), int(signal.get("strength") or 0)
    if vote not in LEVELS or strength < 1:
        return updated
    if signal.get("copy_risk"):
        strength = min(strength, 1)

    current = updated.get("technical_level", "unknown")
    if current != "unknown" and updated.get("technical_level_source") == "inferred":
        if vote != current and strength >= 3 and not signal.get("copy_risk"):
            updated["opposite_strong_signals"] = int(updated.get("opposite_strong_signals") or 0) + 1
            if updated["opposite_strong_signals"] < 2:
                return updated
            updated.update({"technical_level": "unknown", "technical_level_source": "inferred_pending",
                            "technical_confidence": "low", "profiling_valid_turns": 0,
                            "beginner_score": 0, "intermediate_score": 0, "advanced_score": 0,
                            "profiling_evidence_types": [], "opposite_strong_signals": 0,
                            "level_notice_pending": 0, "level_notice_shown": 0})
        elif vote == current:
            updated["opposite_strong_signals"] = 0
            return updated
        else:
            return updated

    score_key = f"{vote}_score"
    updated[score_key] = int(updated.get(score_key) or 0) + strength
    updated["profiling_valid_turns"] = int(updated.get("profiling_valid_turns") or 0) + 1
    evidence = set(updated.get("profiling_evidence_types") or [])
    evidence.update(signal.get("evidence_type") or [])
    updated["profiling_evidence_types"] = sorted(evidence)
    turns = int(updated["profiling_valid_turns"])
    scores = {level: int(updated.get(f"{level}_score") or 0) for level in LEVELS}
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_level, top_score = ranked[0]
    high_confidence = (turns >= 3 and top_score >= 5 and top_score - ranked[1][1] >= 3 and len(evidence) >= 2)
    if high_confidence:
        is_new = updated.get("technical_level") == "unknown"
        updated.update({"technical_level": top_level, "technical_level_source": "inferred",
                        "technical_confidence": "high",
                        "level_notice_pending": 1 if is_new and not updated.get("level_notice_shown") else 0})
    elif turns >= 6 and updated.get("technical_level") == "unknown":
        updated.update({"technical_level": "intermediate", "technical_level_source": "inferred",
                        "technical_confidence": "low", "level_notice_pending": 0})
    return updated


def temporary_level(signal: Dict) -> str:
    return signal["level_vote"] if signal.get("profiling_valid") and signal.get("level_vote") in LEVELS else "unknown"


def profile_notice(level: str) -> str:
    return {
        "advanced": "看你前面几次操作，应该挺熟电脑。后面我会少讲基础概念，直接给判断和排查步骤；我估高了你随时让我讲细一点。",
        "intermediate": "看下来你会自己折腾一些。后面我默认关键步骤讲清楚，太基础的部分少展开，哪里不熟你直接说。",
        "beginner": "后面我会把步骤拆细一点，少丢一堆术语。觉得我讲太细了，随时让我快一点。",
    }.get(level, "")
