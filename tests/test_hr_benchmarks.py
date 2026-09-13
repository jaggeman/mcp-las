"""
Testsvit för HR- och Personalvetarexamen Benchmarks.
Verifierar att AI-systemets juridiska precision överstiger 90%.
"""

import pytest
from src.benchmarks.hr_exam_data import HR_EXAM_BENCHMARKS
from scripts.run_hr_benchmarks import evaluate_single_benchmark, run_all_benchmarks
from src.db.firebase_client import db_client
from src.mcp_tools.tools import search_labor_law

# Benchmarken mater om ratt lagrum HAMTAS, inte hur ett svar ar formulerat.
# Utan lagkorpus faller varje fraga tillbaka pa det lilla som gar att harleda
# utan den, och sviten rapporterar anda en traffsakerhetssiffra - en siffra
# som ser meningsfull ut men inte ar det. Skilj darfor pa de tva fallen.
CORPUS_PROBE = "uppsagningstid anstallningstid manader"


def corpus_state() -> str:
    """'unreachable' (inga credentials), 'empty' (nabar men tom) eller 'ok'."""
    if db_client.db is None:
        return "unreachable"
    return "ok" if search_labor_law(query=CORPUS_PROBE, limit=1) else "empty"


@pytest.fixture
def meaningful_corpus():
    """Hindrar traffsakerhetstesterna fran att rapportera en siffra utan tackning."""
    state = corpus_state()
    if state == "unreachable":
        pytest.skip(
            "Firestore ar inte initierat i den har miljon, sa lagkorpusen saknas "
            "helt. En traffsakerhetssiffra harifran mater ingenting - satt "
            "FIREBASE_CREDENTIALS_PATH och kor om."
        )
    if state == "empty":
        pytest.fail(
            "Firestore ar nabar men lagkorpusen ar TOM. Kor "
            "scripts/ingest_statutes.py innan benchmarken tolkas - annars "
            "mater den bara vad som gar att gissa utan lagtext."
        )


def test_statute_corpus_is_populated():
    """Lagtexten maste finnas innan nagon annan siffra i den har filen betyder nagot."""
    state = corpus_state()
    if state == "unreachable":
        pytest.skip("Firestore ar inte initierat i den har miljon.")
    assert state == "ok", (
        "Lagkorpusen ar tom i den anslutna Firestore-instansen. "
        "search_labor_law returnerar inga traffar for en av de vanligaste "
        "fragorna i svensk arbetsratt."
    )

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

def test_hr_benchmark_individual_cases(meaningful_corpus):
    """Varje enskild HR-fråga ska uppnå minst 80% precision."""
    failures = []
    for item in HR_EXAM_BENCHMARKS:
        res = evaluate_single_benchmark(item)
        if not res["passed"]:
            failures.append(f"{res['id']} failed with score {res['total_score']}%")
    assert len(failures) == 0, f"Benchmark failures: {failures}"

def test_hr_benchmark_overall_accuracy_above_90_pct(meaningful_corpus):
    """Den samlade genomsnittliga träffsäkerheten ska vara minst 90%."""
    report = run_all_benchmarks()
    assert report["overall_average"] >= 90.0, f"Average was {report['overall_average']}%, expected >= 90.0%"
    assert report["passed_count"] == report["total_count"]
