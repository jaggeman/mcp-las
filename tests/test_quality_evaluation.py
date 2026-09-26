"""Offline tests of the evaluator, not evidence of legal correctness."""
import pytest

from src.benchmarks.quality import evaluate_retrieval, parse_reference


def row(country="SE", section="7", **extra):
    return dict(jurisdiction=country, statute="LAS", section=section,
                chapter=None, content="synthetic text", **extra)


@pytest.mark.parametrize("country", ["SE", "DK", "FI", "NO", "DE", "ES", "NL", "GB"])
def test_rank_metrics_and_country_isolation(country):
    expected = [("LAS", None, "7")]
    result = evaluate_retrieval([row(country, "8"), row(country)], expected, country)
    assert result["hit_at_1"] == 0
    assert result["recall_at_5"] == 1
    assert result["reciprocal_rank"] == 0.5
    wrong = "DK" if country == "SE" else "SE"
    result = evaluate_retrieval([row(wrong)], expected, country)
    assert result["recall_at_5"] == 0
    assert result["jurisdiction_match"] is False


def test_empty_and_missing_identity_cannot_pass():
    for rows in ([], [{"content": "LAS 7"}], [row(section="17")]):
        assert evaluate_retrieval(rows, [("LAS", None, "7")], "SE")["recall_at_5"] == 0


def test_reference_requires_same_row_and_exact_chapter():
    rows = [row(section="17"), dict(row(), statute="OTHER")]
    assert evaluate_retrieval(rows, [("LAS", None, "7")], "SE")["recall_at_5"] == 0
    assert evaluate_retrieval([row()], [("LAS", "3", "7")], "SE")["recall_at_5"] == 0


def test_duplicates_do_not_inflate_recall():
    result = evaluate_retrieval([row()] * 5, [("LAS", None, "7"), ("LAS", None, "8")], "SE")
    assert result["recall_at_5"] == 0.5


@pytest.mark.parametrize("reference,expected", [
    ("LAS 7 a §", ("LAS", None, "7a")),
    ("Socialförsäkringsbalken 30 kap. 6 §", ("Socialförsäkringsbalken", "30", "6")),
    ("SFS 1970:215 1 §", ("1970:215", None, "1")),
])
def test_reference_parser(reference, expected):
    assert parse_reference(reference) == expected


def test_benchmark_never_queries_the_answer(monkeypatch):
    from scripts import run_hr_benchmarks as benchmark
    calls = []
    def search(**kwargs):
        calls.append(kwargs["query"])
        return []
    monkeypatch.setattr(benchmark, "search_labor_law", search)
    monkeypatch.setattr(benchmark, "search_case_law", search)
    case = dict(id="synthetic", category="test", question="neutral question",
                expected_statutes=["LAS 7 §"], expected_ad_cases=["AD 2023 nr 45"],
                expected_keywords=["neutral"])
    result = benchmark.evaluate_single_benchmark(case)
    assert calls == ["neutral question", "neutral question"]
    assert result["total_score"] == 0
    assert result["passed"] is False


def test_smoke_rejects_empty_wrong_country_and_error():
    from scripts.production_smoke import validate_search_result
    for result in ({}, {"structuredContent": {"result": []}},
                   {"structuredContent": {"result": [row("DK")]}},
                   {"isError": True, "structuredContent": {"result": [row()]}}):
        with pytest.raises(RuntimeError):
            validate_search_result(result, "SE")
    assert validate_search_result({"structuredContent": {"result": [row()]}}, "SE")


@pytest.mark.parametrize("kind", ["statute", "calculation", "cba", "precedent", "general"])
def test_certainty_is_not_an_unmeasured_probability(kind):
    from src.mcp_tools.tools import _determine_certainty
    certainty = _determine_certainty("synthetic text", kind)
    assert certainty["score_pct"] is None
    assert certainty["measurement"] == "not_calibrated"
    assert "%" not in certainty["badge"]


def test_all_legacy_references_have_supported_syntax():
    from src.benchmarks.hr_exam_data import HR_EXAM_BENCHMARKS
    for case in HR_EXAM_BENCHMARKS:
        for reference in case.get("expected_statutes", []):
            assert parse_reference(reference)


def test_empty_gold_is_not_a_perfect_score():
    with pytest.raises(ValueError):
        evaluate_retrieval([row()], [], "SE")


def test_smoke_law_names_are_not_substring_matches():
    from scripts.production_smoke import _matches_expected
    assert not _matches_expected(dict(row(), statute="NOT-LAS"), [("LAS", None, "7")])
