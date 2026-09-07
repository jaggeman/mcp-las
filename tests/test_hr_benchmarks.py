"""
Testsvit för HR- och Personalvetarexamen Benchmarks.
Verifierar att AI-systemets juridiska precision överstiger 90%.
"""

import pytest
from src.benchmarks.hr_exam_data import HR_EXAM_BENCHMARKS
from scripts.run_hr_benchmarks import evaluate_single_benchmark, run_all_benchmarks

def test_hr_benchmark_dataset_integrity():
    """Säkerställer att benchmark-datamängden har minst 50 validerade frågor."""
    assert len(HR_EXAM_BENCHMARKS) >= 50
    categories = set(item["category"] for item in HR_EXAM_BENCHMARKS)
    assert len(categories) == 6
    assert "Uppsägning & Sakliga Skäl" in categories
    assert "Arbetsbrist & Turordning" in categories
    assert "MBL & Kollektivavtal" in categories
    assert "Semester & Arbetstid" in categories
    assert "Rehabilitering & Myndigheter" in categories or "Diskriminering & Likabehandling" in categories

def test_hr_benchmark_individual_cases():
    """Varje enskild HR-fråga ska uppnå minst 80% precision."""
    failures = []
    for item in HR_EXAM_BENCHMARKS:
        res = evaluate_single_benchmark(item)
        if not res["passed"]:
            failures.append(f"{res['id']} failed with score {res['total_score']}%")
    assert len(failures) == 0, f"Benchmark failures: {failures}"

def test_hr_benchmark_overall_accuracy_above_90_pct():
    """Den samlade genomsnittliga träffsäkerheten ska vara minst 90%."""
    report = run_all_benchmarks()
    assert report["overall_average"] >= 90.0, f"Average was {report['overall_average']}%, expected >= 90.0%"
    assert report["passed_count"] == report["total_count"]
