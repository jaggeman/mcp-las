"""Audit the bundled AD catalogue against Arbetsdomstolen's public archives.

This module only establishes whether a case number exists and whether AD has
published a referat.  It deliberately does not treat a local summary as legally
verified merely because the case number exists.
"""

from __future__ import annotations

import requests

from src.benchmarks.decider_quality import DEFAULT_MODEL
from src.benchmarks.decider_quality_data import ANSWER_QUESTIONS
from src.scrapers.arbetsdomstolen_fetcher import (
    fetch_archive_year,
    normalize_case_number,
    parse_archive_page,
)


def audit_local_cases(
    local_cases: list[dict],
    official_cases: dict[str, dict],
    *,
    unavailable_years: set[int] | None = None,
) -> dict:
    unavailable_years = unavailable_years or set()
    rows = []
    counts = {
        "total": len(local_cases),
        "official_summary": 0,
        "unreported": 0,
        "missing": 0,
        "archive_unavailable": 0,
    }
    for local_case in local_cases:
        case_number = normalize_case_number(str(local_case.get("case_number") or ""))
        official = official_cases.get(case_number) if case_number else None
        year = int(local_case.get("year") or 0)
        status = (
            official["status"] if official
            else "archive_unavailable" if year in unavailable_years
            else "missing"
        )
        counts[status] += 1
        rows.append({
            "case_number": case_number or local_case.get("case_number"),
            "status": status,
            "source_url": official.get("source_url") if official else None,
            "official_summary": official.get("official_summary") if official else None,
            "local_case": local_case,
        })
    return {
        "counts": counts,
        "unavailable_years": sorted(unavailable_years),
        "cases": rows,
    }


def fetch_and_audit(local_cases: list[dict], *, session=None, timeout: float = 30) -> dict:
    official_cases = {}
    unavailable_years = set()
    for year in sorted({int(case["year"]) for case in local_cases}):
        try:
            official_cases.update(fetch_archive_year(year, session=session, timeout=timeout))
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                unavailable_years.add(year)
                continue
            raise
    return audit_local_cases(
        local_cases,
        official_cases,
        unavailable_years=unavailable_years,
    )


def _local_draft(case: dict) -> str:
    fields = ("title", "summary", "domskal", "slut", "parties")
    return "\n".join(
        f"{field}: {case[field]}" for field in fields
        if str(case.get(field) or "").strip()
    )


def _noul_prediction(answer: dict) -> tuple[bool, float]:
    value = answer.get("noul") if isinstance(answer, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError("Invalid Decider noul answer")
    value = float(value)
    return value >= 0.5, abs(2 * value - 1)


def classify_verifiable_cases(audit_report: dict, client, *, model=DEFAULT_MODEL) -> dict:
    """Shadow-classify local summaries against public AD referats.

    The result intentionally excludes both source text and local draft text.  A
    model classification is triage, not a legal verification or correctness score.
    """
    rows = []
    counts = {
        "audited": 0,
        "fully_supported": 0,
        "partially_supported": 0,
        "unsupported": 0,
    }
    for case in audit_report["cases"]:
        if case["status"] != "official_summary" or not case["official_summary"]:
            continue
        request = {
            "model": model,
            "state": {
                "requested_jurisdiction": "SE",
                "case_number": case["case_number"],
                "official_source_excerpt": case["official_summary"],
                "local_draft": _local_draft(case["local_case"]),
                "evaluation_scope": (
                    "Compare the local draft only with the supplied official Arbetsdomstolen "
                    "excerpt. Do not use outside knowledge. Every material local claim must "
                    "be supported by the excerpt."
                ),
            },
            "questions": ANSWER_QUESTIONS,
        }
        response = client.decide(request)
        answers = response.get("answers") if isinstance(response, dict) else None
        if not isinstance(answers, dict) or set(answers) != set(ANSWER_QUESTIONS):
            raise ValueError("Decider response does not match AD audit questions")
        jurisdiction, jurisdiction_confidence = _noul_prediction(
            answers["jurisdiction_consistent"]
        )
        grounded, grounded_confidence = _noul_prediction(answers["claims_grounded"])
        support_answer = answers["source_support"]
        support = support_answer.get("choice") if isinstance(support_answer, dict) else None
        if support not in {"fully_supported", "partially_supported", "unsupported"}:
            raise ValueError("Invalid Decider source-support answer")
        support_confidence = support_answer.get("confidence")
        if (isinstance(support_confidence, bool)
                or not isinstance(support_confidence, (int, float))
                or not 0 <= support_confidence <= 1):
            raise ValueError("Invalid Decider source-support confidence")
        counts["audited"] += 1
        counts[support] += 1
        rows.append({
            "case_number": case["case_number"],
            "source_url": case["source_url"],
            "jurisdiction_consistent": jurisdiction,
            "source_support": support,
            "claims_grounded": grounded,
            "gate_confidence": round(min(
                jurisdiction_confidence,
                float(support_confidence),
                grounded_confidence,
            ), 6),
            "latency_ms": round(float(response.get("latency_ms", 0) or 0), 2),
        })
    return {
        "measurement": "model_triage_against_public_ad_referats_not_legal_correctness",
        "source_counts": audit_report["counts"],
        "counts": counts,
        "cases": rows,
    }
