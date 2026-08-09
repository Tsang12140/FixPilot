"""No-network regression tests for roast-mode UI effects."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import memes, service


results = []


def check(case_id, name, fn):
    try:
        fn()
        results.append({"id": case_id, "name": name, "status": "PASS"})
    except Exception as exc:
        results.append({"id": case_id, "name": name, "status": "FAIL", "detail": str(exc)})


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def normal_assistant(count):
    return [{"role": "assistant", "content": f"normal reply {index}"} for index in range(count)]


def test_asset_curation():
    require("sick" not in memes.MEME_ASSETS, "removed meme is still active")
    require(all("sick" not in pool for pool in memes.MEME_POOLS.values()), "removed meme remains selectable")
    require("stop_bothering" in memes.MEME_ASSETS, "approved meme disappeared")
    require("cool_gun" in memes.MEME_ASSETS, "approved meme disappeared")


def test_marker_compatibility():
    require(memes.reaction_id_from_message("6") == "six", "legacy six was not recognized")
    require(memes.reaction_id_from_message("[REACTION:six]") == "six", "semantic six marker failed")
    require(memes.reaction_id_from_message("[REACTION:chichi]") == "chichi", "chichi marker failed")
    require(memes.is_ui_effect_message("[MEME:cool_gun]"), "meme is not excluded from context")
    require(memes.is_ui_effect_message("[REACTION:chichi]"), "reaction is not excluded from context")


def test_six_never_repeats():
    history = [{"role": "assistant", "content": "[REACTION:six]"}] + normal_assistant(3)
    effect = memes.choose_joke_effect("cool", history, random_value=0.01)
    require(effect is not None and effect.get("kind") == "meme", "six repeated instead of using a meme")


def test_acknowledgements_are_quiet():
    require(memes.is_acknowledgement("\u8c22\u8c22"), "thanks acknowledgement not detected")
    require(not memes.can_emit_reaction([], "\u8c22\u8c22"), "acknowledgement can still emit a reaction")


def test_cooldown():
    history = [{"role": "assistant", "content": "[REACTION:six]"}] + normal_assistant(1)
    require(not memes.can_emit_reaction(history, "new diagnostic detail"), "reaction cooldown did not block")
    history = [{"role": "assistant", "content": "[REACTION:six]"}] + normal_assistant(3)
    require(memes.can_emit_reaction(history, "new diagnostic detail"), "reaction cooldown stayed blocked too long")


def test_chichi_is_compact_reaction():
    effect = memes.choose_joke_effect("chichi", [], random_value=0.5)
    require(effect == {"kind": "reaction", "reaction": "chichi"}, "chichi did not resolve to a reaction card")


def test_normalized_context_omits_ui_effects():
    normalized = service.normalize_messages([
        {"role": "user", "content": "ordinary user context"},
        {"role": "assistant", "content": "[REACTION:chichi]"},
        {"role": "assistant", "content": "[MEME:cool_gun]"},
        {"role": "assistant", "content": "ordinary reply"},
    ])
    contents = [item["content"] for item in normalized]
    require("[REACTION:chichi]" not in contents, "reaction leaked into model context")
    require("[MEME:cool_gun]" not in contents, "meme leaked into model context")
    require("ordinary reply" in contents, "ordinary assistant context was removed")


check("M01", "active meme pool excludes rejected asset", test_asset_curation)
check("M02", "semantic reactions preserve legacy compatibility and context exclusion", test_marker_compatibility)
check("M03", "six cannot repeat in one conversation", test_six_never_repeats)
check("M04", "acknowledgements do not trigger reactions", test_acknowledgements_are_quiet)
check("M05", "reaction cooldown needs three ordinary assistant replies", test_cooldown)
check("M06", "chichi is a compact semantic reaction", test_chichi_is_compact_reaction)
check("M07", "UI-only reactions never leak into model context", test_normalized_context_omits_ui_effects)

payload = {"suite": "memes", "results": results}
failed = any(item["status"] != "PASS" for item in results)
if "--json" in sys.argv:
    print(json.dumps(payload, ensure_ascii=False))
else:
    for item in results:
        suffix = f" ({item['detail']})" if item.get("detail") else ""
        print(f"[{item['id']}] {item['name']}: {item['status']}{suffix}")
raise SystemExit(1 if failed else 0)
