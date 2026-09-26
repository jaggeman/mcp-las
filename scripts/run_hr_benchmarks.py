"""Retrieval diagnostics against legacy HR expectations, not legal accuracy.

Only the question is supplied to retrievers. Gold references are scorer-only.
The legacy dataset still requires independent legal review.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.benchmarks.hr_exam_data import HR_EXAM_BENCHMARKS
from src.benchmarks.quality import evaluate_retrieval, parse_reference
from src.mcp_tools.tools import search_labor_law, search_case_law


def _case_id(value):
    match = re.fullmatch(r"(?:AD\s*)?(\d{4})\s*(?:nr|:)\s*(\d+)", str(value).strip(), re.I)
    return match.groups() if match else None


def evaluate_single_benchmark(item):
    question = item["question"]
    country = item.get("jurisdiction", "SE")
    references = [parse_reference(value) for value in item.get("expected_statutes", [])]
    cases = item.get("expected_ad_cases", [])
    rows = search_labor_law(query=question, jurisdiction=country, limit=10)
    ad_rows = search_case_law(query=question, limit=10) if cases and country == "SE" else []
    metrics = evaluate_retrieval(rows, references, country) if references else None
    statute_score = metrics["recall_at_10"] * 100 if metrics else None
    found_cases = {_case_id(row.get("case_number")) for row in ad_rows}
    ad_score = (100 * sum(_case_id(value) is not None and _case_id(value) in found_cases
                          for value in cases) / len(cases)) if cases else None
    # Keyword presence is diagnostic only: it cannot establish correctness.
    corpus = " ".join(str(row.get(field, "")) for row in rows + ad_rows
                      for field in ("content", "summary", "domskal")).casefold()
    keywords = item.get("expected_keywords", [])
    keyword_score = 100 * sum(value.casefold() in corpus for value in keywords) / len(keywords) if keywords else None
    scores = [score for score in (statute_score, ad_score) if score is not None]
    total = sum(scores) / len(scores) if scores else 0.0
    return {
        "id": item["id"], "category": item["category"], "question": question,
        "total_score": round(total, 1), "statute_score": statute_score,
        "ad_score": ad_score, "keyword_score": keyword_score,
        "retrieval": metrics, "evaluated": bool(scores),
        "passed": bool(scores) and all(score >= 80 for score in scores)
                  and (metrics is None or metrics["jurisdiction_match"]),
        "measurement": "retrieval_only_not_legal_correctness",
        "reference_review_status": "legacy_unverified",
    }


def run_all_benchmarks():
    results = [evaluate_single_benchmark(item) for item in HR_EXAM_BENCHMARKS]
    if not results:
        raise ValueError("Benchmark dataset is empty")
    categories = {}
    for result in results:
        categories.setdefault(result["category"], []).append(result["total_score"])
    report = {
        "overall_average": round(sum(row["total_score"] for row in results) / len(results), 1),
        "passed_count": sum(row["passed"] for row in results),
        "total_count": len(results),
        "category_averages": {key: sum(values) / len(values) for key, values in categories.items()},
        "measurement": "retrieval_only_not_legal_correctness",
        "reference_review_status": "legacy_unverified", "results": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    report = run_all_benchmarks()
    sys.exit(0 if report["passed_count"] == report["total_count"] else 1)
