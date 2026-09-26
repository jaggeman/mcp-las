"""Measure deterministic top-1 statute search quality against ground truth."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.benchmarks.search_quality_data import SEARCH_QUALITY_CASES
from src.benchmarks.quality import matches_reference
from src.mcp_tools.tools import search_labor_law


def _normalized(value):
    return str(value or "").lower().replace(" ", "")


def is_expected(result, expected):
    return any(matches_reference(result, reference) for reference in expected)


def run():
    rows = []
    for case in SEARCH_QUALITY_CASES:
        country = case["jurisdiction"]
        results = search_labor_law(case["question"], jurisdiction=country, limit=3)
        top = results[0] if results else {}
        rows.append({
            "id": case["id"],
            "jurisdiction": country,
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
