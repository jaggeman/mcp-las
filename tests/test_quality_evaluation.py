"""Offline tests of the evaluator, not evidence of legal correctness."""
import pytest

from src.benchmarks.quality import evaluate_retrieval, is_official_source_url, parse_reference


def row(country="SE", section="7", **extra):
    value = dict(jurisdiction=country, statute="LAS", section=section,
                 chapter=None, content="synthetic text",
                 source_url="https://data.riksdagen.se/dokument/sfs-1982-80.html")
    value.update(extra)
    return value


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
                   {"structuredContent": {"result": [row(source_url=None)]}},
                   {"structuredContent": {"result": [row(source_url="https://example.test/fake")]}} ,
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


@pytest.mark.parametrize("country,url", [
    ("SE", "https://data.riksdagen.se/dokument/sfs-1982-80.html"),
    ("DK", "https://www.retsinformation.dk/eli/lta/2024/1"),
    ("FI", "https://www.finlex.fi/fi/laki/ajantasa/2001/20010055"),
    ("NO", "https://lovdata.no/dokument/NL/lov/2005-06-17-62"),
    ("DE", "https://www.gesetze-im-internet.de/kschg/"),
    ("ES", "https://www.boe.es/buscar/act.php?id=BOE-A-2015-11430"),
    ("NL", "https://wetten.overheid.nl/BWBR0005290"),
    ("GB", "https://www.legislation.gov.uk/ukpga/1996/18"),
])
def test_only_official_source_hosts_are_accepted(country, url):
    assert is_official_source_url(url, country)
    assert not is_official_source_url("https://example.test/copied-law", country)
    assert not is_official_source_url(f"http://{url.split('/')[2]}/insecure", country)


def test_search_quality_cases_cover_every_supported_country_with_reviewed_foreign_gold():
    from src.benchmarks.search_quality_data import SEARCH_QUALITY_CASES

    assert {case["jurisdiction"] for case in SEARCH_QUALITY_CASES} == {
        "SE", "DK", "FI", "NO", "DE", "ES", "NL", "GB",
    }
    assert len({case["id"] for case in SEARCH_QUALITY_CASES}) == len(SEARCH_QUALITY_CASES)
    for case in SEARCH_QUALITY_CASES:
        assert case["expected"]
        if case["jurisdiction"] != "SE":
            assert case["reviewed_at"] == "2026-09-26"
            assert is_official_source_url(case["official_reference"], case["jurisdiction"])


def test_quality_smoke_uses_each_cases_jurisdiction():
    from scripts.production_smoke import run_search_quality

    calls = []

    class Client:
        def request(self, _method, params):
            calls.append(params["arguments"]["jurisdiction"])
            country = params["arguments"]["jurisdiction"]
            return {"structuredContent": {"result": [{
                "jurisdiction": country, "statute": "Law", "section": "1",
                "content": "text", "source_url": {
                    "DK": "https://www.retsinformation.dk/eli/lta/2024/1",
                    "FI": "https://data.finlex.fi/fi/lainsaadanto/2001/55",
                }[country],
            }]}}

    cases = [
        {"id": "dk", "question": "q", "jurisdiction": "DK", "expected": [("Law", None, "1")]},
        {"id": "fi", "question": "q", "jurisdiction": "FI", "expected": [("Law", None, "1")]},
    ]
    assert run_search_quality(Client(), cases) == []
    assert calls == ["DK", "FI"]
