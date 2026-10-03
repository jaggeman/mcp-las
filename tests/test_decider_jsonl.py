"""JSONL ingestion tests for anonymised Decider shadow evaluations."""

import json

import pytest

from src.benchmarks.decider_answer_jsonl import load_answer_cases, summarize_cases


def valid_row(**changes):
    row = {
        "id": "case-1",
        "jurisdiction": "SE",
        "question": "Synthetic question",
        "source_excerpts": ["Synthetic official-source excerpt"],
        "draft_answer": "Synthetic draft",
        "expected": {
            "jurisdiction_consistent": True,
            "source_support": "fully_supported",
            "claims_grounded": True,
        },
        "review_status": "synthetic_unverified",
    }
    row.update(changes)
    return row


def write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_loader_builds_model_cases_without_putting_gold_in_state(tmp_path):
    path = tmp_path / "cases.jsonl"
    write_jsonl(path, [valid_row()])

    cases = load_answer_cases(path)

    assert len(cases) == 1
    assert cases[0]["id"] == "case-1"
    assert cases[0]["suite"] == "answer_quality"
    assert cases[0]["state"]["requested_jurisdiction"] == "SE"
    assert cases[0]["expected"]["source_support"] == "fully_supported"
    assert "expected" not in json.dumps(cases[0]["state"])
    assert cases[0]["review_status"] == "synthetic_unverified"


def test_summary_contains_metadata_but_no_case_content(tmp_path):
    path = tmp_path / "cases.jsonl"
    rows = [valid_row(), valid_row(id="case-2", jurisdiction="DK")]
    write_jsonl(path, rows)
    cases = load_answer_cases(path)

    summary = summarize_cases(cases)

    assert summary == {
        "case_count": 2,
        "by_jurisdiction": {"DK": 1, "SE": 1},
        "by_review_status": {"synthetic_unverified": 2},
    }
    serialized = json.dumps(summary)
    assert "Synthetic question" not in serialized
    assert "Synthetic draft" not in serialized
    assert "official-source excerpt" not in serialized


def test_human_review_status_requires_auditable_metadata(tmp_path):
    path = tmp_path / "cases.jsonl"
    write_jsonl(path, [valid_row(review_status="human_reviewed")])
    with pytest.raises(ValueError, match="reviewed_by"):
        load_answer_cases(path)

    write_jsonl(path, [valid_row(
        review_status="human_reviewed", reviewed_by="legal-reviewer",
        reviewed_at="2026-10-03",
    )])
    case = load_answer_cases(path)[0]
    assert case["review_status"] == "human_reviewed"


@pytest.mark.parametrize("mutation,error", [
    ({"jurisdiction": "US"}, "jurisdiction"),
    ({"source_excerpts": []}, "source_excerpts"),
    ({"source_excerpts": ["ok", 3]}, "source_excerpts"),
    ({"draft_answer": ""}, "draft_answer"),
    ({"question": ""}, "question"),
    ({"review_status": "approved"}, "review_status"),
    ({"expected": {"jurisdiction_consistent": True}}, "expected"),
    ({"expected": {"jurisdiction_consistent": True,
                    "source_support": "maybe",
                    "claims_grounded": True}}, "source_support"),
])
def test_loader_rejects_invalid_cases(tmp_path, mutation, error):
    path = tmp_path / "cases.jsonl"
    write_jsonl(path, [valid_row(**mutation)])
    with pytest.raises(ValueError, match=error):
        load_answer_cases(path)


def test_loader_rejects_duplicate_ids_and_invalid_json(tmp_path):
    path = tmp_path / "cases.jsonl"
    write_jsonl(path, [valid_row(), valid_row()])
    with pytest.raises(ValueError, match="Duplicate"):
        load_answer_cases(path)

    path.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        load_answer_cases(path)


def test_loader_rejects_unknown_fields_to_catch_sensitive_data(tmp_path):
    path = tmp_path / "cases.jsonl"
    write_jsonl(path, [valid_row(employee_name="PRIVATE")])
    with pytest.raises(ValueError, match="unsupported fields"):
        load_answer_cases(path)


def test_checked_in_shadow_dataset_is_balanced_and_unverified():
    from src.benchmarks.decider_quality_data import ANSWER_QUESTIONS
    from pathlib import Path

    path = Path(__file__).parent / "data" / "decider_answer_cases.jsonl"
    cases = load_answer_cases(path)
    summary = summarize_cases(cases)

    assert summary["case_count"] >= 32
    assert summary["by_jurisdiction"] == {
        "DE": 4, "DK": 4, "ES": 4, "FI": 4,
        "GB": 4, "NL": 4, "NO": 4, "SE": 4,
    }
    assert summary["by_review_status"] == {"synthetic_unverified": 32}
    assert "each clause" in ANSWER_QUESTIONS["claims_grounded"]["instructions"].lower()
    assert "plausible" in ANSWER_QUESTIONS["source_support"]["instructions"].lower()
