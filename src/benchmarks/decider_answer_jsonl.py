"""Strict JSONL loader for local/shadow answer-quality evaluation.

The loader deliberately accepts a small schema so accidental identifiers or
other fields do not silently become model input.  It does not anonymise data;
callers must provide already anonymised cases.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

from src.benchmarks.decider_quality_data import ANSWER_QUESTIONS
from src.jurisdictions import JURISDICTIONS


MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_CASES = 1000
MAX_TEXT_CHARS = 20_000
MAX_EXCERPTS = 10
ALLOWED_FIELDS = {
    "id", "jurisdiction", "question", "source_excerpts", "draft_answer",
    "expected", "review_status", "reviewed_by", "reviewed_at",
}
EXPECTED_FIELDS = {"jurisdiction_consistent", "source_support", "claims_grounded"}
SUPPORT_VALUES = {"fully_supported", "partially_supported", "unsupported"}
REVIEW_STATUSES = {"synthetic_unverified", "human_reviewed"}


def _text(value, field, *, limit=MAX_TEXT_CHARS):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    if len(value) > limit:
        raise ValueError(f"{field} exceeds {limit} characters")
    return value.strip()


def _validate_expected(value, line_number):
    if not isinstance(value, dict) or set(value) != EXPECTED_FIELDS:
        raise ValueError(f"line {line_number}: expected must contain exactly {sorted(EXPECTED_FIELDS)}")
    if not isinstance(value["jurisdiction_consistent"], bool):
        raise ValueError(f"line {line_number}: expected jurisdiction_consistent must be boolean")
    if not isinstance(value["claims_grounded"], bool):
        raise ValueError(f"line {line_number}: expected claims_grounded must be boolean")
    if value["source_support"] not in SUPPORT_VALUES:
        raise ValueError(f"line {line_number}: expected source_support is invalid")
    return dict(value)


def _validate_row(row, line_number):
    if not isinstance(row, dict):
        raise ValueError(f"line {line_number}: each case must be a JSON object")
    unknown = set(row) - ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"line {line_number}: unsupported fields: {sorted(unknown)}")
    required = {"id", "jurisdiction", "question", "source_excerpts", "draft_answer",
                "expected", "review_status"}
    missing = required - set(row)
    if missing:
        raise ValueError(f"line {line_number}: missing fields: {sorted(missing)}")

    case_id = _text(row["id"], f"line {line_number}: id", limit=128)
    jurisdiction = _text(row["jurisdiction"], f"line {line_number}: jurisdiction", limit=2).upper()
    if jurisdiction not in JURISDICTIONS:
        raise ValueError(f"line {line_number}: jurisdiction must be one of {', '.join(JURISDICTIONS)}")
    question = _text(row["question"], f"line {line_number}: question")
    draft = _text(row["draft_answer"], f"line {line_number}: draft_answer")

    excerpts = row["source_excerpts"]
    if not isinstance(excerpts, list) or not 1 <= len(excerpts) <= MAX_EXCERPTS:
        raise ValueError(f"line {line_number}: source_excerpts must contain 1-{MAX_EXCERPTS} strings")
    clean_excerpts = []
    for index, excerpt in enumerate(excerpts, 1):
        clean_excerpts.append(_text(
            excerpt, f"line {line_number}: source_excerpts[{index}]"
        ))

    status = row["review_status"]
    if status not in REVIEW_STATUSES:
        raise ValueError(f"line {line_number}: review_status must be one of {sorted(REVIEW_STATUSES)}")
    reviewer = row.get("reviewed_by")
    reviewed_at = row.get("reviewed_at")
    if status == "human_reviewed":
        reviewer = _text(reviewer, f"line {line_number}: reviewed_by", limit=128)
        reviewed_at = _text(reviewed_at, f"line {line_number}: reviewed_at", limit=10)
        try:
            date.fromisoformat(reviewed_at)
        except ValueError as exc:
            raise ValueError(f"line {line_number}: reviewed_at must be YYYY-MM-DD") from exc
    elif reviewer is not None or reviewed_at is not None:
        raise ValueError(
            f"line {line_number}: reviewed_by/reviewed_at require review_status=human_reviewed"
        )

    return {
        "id": case_id,
        "suite": "answer_quality",
        "review_status": status,
        "reviewed_by": reviewer,
        "reviewed_at": reviewed_at,
        "state": {
            "requested_jurisdiction": jurisdiction,
            "user_question": question,
            "source_excerpts": clean_excerpts,
            "draft_answer": draft,
            "evaluation_scope": (
                "Judge only whether the draft is supported by the supplied excerpts. "
                "Do not use outside knowledge. Translation language does not change jurisdiction."
            ),
        },
        "questions": ANSWER_QUESTIONS,
        "expected": _validate_expected(row["expected"], line_number),
    }


def load_answer_cases(path):
    """Load already-anonymised answer cases from a bounded UTF-8 JSONL file."""
    path = Path(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"JSONL input exceeds {MAX_FILE_BYTES} bytes")
    cases = []
    seen = set()
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            if len(cases) >= MAX_CASES:
                raise ValueError(f"JSONL input exceeds {MAX_CASES} cases")
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}") from exc
            case = _validate_row(raw, line_number)
            if case["id"] in seen:
                raise ValueError(f"Duplicate case id on line {line_number}: {case['id']}")
            seen.add(case["id"])
            cases.append(case)
    if not cases:
        raise ValueError("JSONL input contains no cases")
    return cases


def summarize_cases(cases):
    """Return non-content metadata suitable for logs and reports."""
    return {
        "case_count": len(cases),
        "by_jurisdiction": dict(sorted(Counter(
            case["state"]["requested_jurisdiction"] for case in cases
        ).items())),
        "by_review_status": dict(sorted(Counter(
            case["review_status"] for case in cases
        ).items())),
    }
