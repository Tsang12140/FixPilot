"""No-network checks for the curated official-reference registry."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from app import official_sources


def assert_true(condition, detail):
    if not condition:
        raise AssertionError(detail)


def test_registry_json_and_counts_are_consistent():
    data = json.loads(Path(ROOT, "data", "official_sources.json").read_text(encoding="utf-8"))
    official = data["official_sources"]
    verified = "\u5df2\u9a8c\u8bc1"
    pending = "\u5f85\u6838\u9a8c"
    assert_true(data["_meta"].get("schema_version") == 1, "registry schema version is missing")
    assert_true(data["_meta"]["total_official"] == len(official), "official source count is stale")
    assert_true(data["_meta"]["verified_count"] == sum(item["review_status"] == verified for item in official), "verified count is stale")
    assert_true(data["_meta"]["pending_review_count"] == sum(item["review_status"] == pending for item in official), "pending count is stale")


def test_enabled_records_are_routable_official_sources():
    data = official_sources.load_registry()
    enabled = [item for item in data["official_sources"] if item.get("enabled")]
    assert_true(enabled, "registry has no enabled official sources")
    for item in enabled:
        assert_true(official_sources.is_enabled_verified_official(item), f"{item['id']} is enabled but not a verified official runtime source")
        assert_true(bool(item.get("domains")), f"{item['id']} has no allowlisted domains")
        assert_true(bool(item.get("required_identifiers")), f"{item['id']} has no identifier requirement")


def test_nonofficial_sources_stay_disabled():
    data = official_sources.load_registry()
    for item in data.get("citation_only_sources", []):
        assert_true(not item.get("enabled"), f"nonofficial source {item['id']} must remain disabled")
        assert_true(item.get("source_tier") == "nonofficial_reference_only", f"nonofficial source {item['id']} has the wrong tier")


def test_high_risk_sources_require_identity_and_confirmation():
    data = official_sources.load_registry()
    for item in data["official_sources"]:
        if item.get("risk_level") == "high" and item.get("enabled"):
            assert_true(item.get("high_risk_confirmation_required") is True, f"{item['id']} misses high-risk confirmation")
            assert_true(item.get("requires_target_confirmation") is True, f"{item['id']} misses target confirmation")
            if "model" in (item.get("required_identifiers") or []):
                assert_true(item.get("requires_exact_model") is True, f"{item['id']} accepts a model lookup without exact model")


def test_registry_selection_is_conservative_and_brand_scoped():
    official_sources.clear_registry_cache()
    assert_true(not official_sources.select_official_sources("computer blue screen"), "generic symptom must not unlock external lookup")
    sources = official_sources.select_official_sources("asus B650M-PLUS BIOS manual")
    assert_true(sources and all(item["vendor"] == "ASUS" for item in sources), "ASUS model did not select only ASUS sources")
    chinese_sources = official_sources.select_official_sources("\u534e\u7855 B650M-PLUS BIOS \u624b\u518c")
    assert_true(chinese_sources and all(item["vendor"] == "ASUS" for item in chinese_sources), "Chinese vendor alias did not select ASUS sources")
    assert_true({"asus.com", "asus.com.cn"} == official_sources.allowed_domains(sources), "ASUS domains were not normalized")
    assert_true(not any(item["id"] == "colorful_official" for item in official_sources.select_official_sources("colorful CVN B650M BIOS")), "pending Colorful source was routed")


def test_domain_filter_rejects_suffix_and_non_https_confusion():
    domains = {"asus.com"}
    assert_true(official_sources.is_allowed_url("https://www.asus.com/support", domains), "official subdomain was rejected")
    assert_true(not official_sources.is_allowed_url("https://asus.com.example.test/manual", domains), "suffix-confusion domain was accepted")
    assert_true(not official_sources.is_allowed_url("ftp://www.asus.com/file", domains), "non-HTTP source was accepted")


TESTS = [
    ("S01", "registry JSON and metadata counts agree", test_registry_json_and_counts_are_consistent),
    ("S02", "enabled records are verified official runtime sources", test_enabled_records_are_routable_official_sources),
    ("S03", "nonofficial reference sources stay disabled", test_nonofficial_sources_stay_disabled),
    ("S04", "high-risk sources require exact identity and confirmation", test_high_risk_sources_require_identity_and_confirmation),
    ("S05", "selection stays conservative and brand-scoped", test_registry_selection_is_conservative_and_brand_scoped),
    ("S06", "domain filtering rejects lookalikes and non-HTTP URLs", test_domain_filter_rejects_suffix_and_non_https_confusion),
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
    parser = __import__("argparse").ArgumentParser(description="Official-source registry regression suite")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = run_tests()
    if args.json:
        print(json.dumps({"suite": "sources", "results": results}, ensure_ascii=False))
    else:
        for result in results:
            suffix = f": {result.get('detail')}" if result.get("detail") else ""
            print(f"[{result['id']}] {result['name']}: {result['status']}{suffix}")
    raise SystemExit(0 if all(result["status"] == "PASS" for result in results) else 1)


if __name__ == "__main__":
    main()
