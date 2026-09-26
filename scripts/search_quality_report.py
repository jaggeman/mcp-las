"""Measure deterministic top-1 statute search quality against ground truth."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.benchmarks.search_quality_data import SEARCH_QUALITY_CASES
from src.mcp_tools.tools import search_labor_law


def _normalized(value):
    return str(value or "").lower().replace(" ", "")


def is_expected(result, expected):
    law = _normalized(result.get("statute") or result.get("statute_short") or result.get("statute_id"))
    chapter = _normalized(result.get("chapter"))
    section = _normalized(result.get("section") or result.get("section_number"))
    for wanted_law, wanted_chapter, wanted_section in expected:
        if _normalized(wanted_law) not in law:
            continue
        if wanted_chapter is not None and chapter != _normalized(wanted_chapter):
            continue
        if section == _normalized(wanted_section):
            return True
    return False


def run():
    rows = []
    for case in SEARCH_QUALITY_CASES:
        results = search_labor_law(case["question"], jurisdiction="SE", limit=3)
        top = results[0] if results else {}
        rows.append({
            "id": case["id"],
            "passed": bool(top) and is_expected(top, case["expected"]),
            "actual": {
                "law": top.get("statute") or top.get("statute_short"),
                "chapter": top.get("chapter"),
                "section": top.get("section") or top.get("section_number"),
            },
        })
    passed = sum(row["passed"] for row in rows)
    report = {"passed": passed, "total": len(rows), "top1_rate": passed / len(rows), "cases": rows}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    run()
