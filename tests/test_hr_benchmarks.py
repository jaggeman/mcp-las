"""
Testsvit för HR- och Personalvetarexamen Benchmarks.
Kontrollerar återhämtning av äldre förväntade referenser, inte juridisk precision.
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

def test_hr_benchmark_individual_cases_report_failures_honestly(meaningful_corpus):
    """Det ogranskade facit ska ge diagnostik utan falska godkännanden."""
    for item in HR_EXAM_BENCHMARKS:
        result = evaluate_single_benchmark(item)
        assert result["reference_review_status"] == "legacy_unverified"
        assert result["measurement"] == "retrieval_only_not_legal_correctness"
        assert 0 <= result["total_score"] <= 100
        component_scores = [
            score for score in (result["statute_score"], result["ad_score"])
            if score is not None
        ]
        assert result["passed"] == (
            bool(component_scores)
            and all(score >= 80 for score in component_scores)
            and (result["retrieval"] is None or result["retrieval"]["jurisdiction_match"])
        )

def test_hr_benchmark_report_is_internally_consistent(meaningful_corpus):
    """Rapporten får inte beskrivas som juridisk precision innan facit granskats."""
    report = run_all_benchmarks()
    assert report["reference_review_status"] == "legacy_unverified"
    assert report["measurement"] == "retrieval_only_not_legal_correctness"
    assert report["total_count"] == len(HR_EXAM_BENCHMARKS)
    assert report["passed_count"] == sum(result["passed"] for result in report["results"])
    assert report["overall_average"] == round(
        sum(result["total_score"] for result in report["results"]) / report["total_count"], 1
    )
