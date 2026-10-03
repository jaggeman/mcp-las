"""Tests for the optional Strands Decider quality PoC."""

import json

import pytest

from src.benchmarks.decider_quality import (
    DeciderHTTPClient,
    build_request,
    evaluate_cases,
)


CASES = [
    {
        "id": "supported",
        "suite": "answer_quality",
        "state": {"requested_jurisdiction": "SE", "question": "q", "sources": ["s"], "draft_answer": "a"},
        "questions": {
            "source_support": {
                "type": "choice",
                "instructions": "support?",
                "criteria": {
                    "fully_supported": "all claims",
                    "partially_supported": "some claims",
                    "unsupported": "no claims",
                },
            },
            "overclaim": {"type": "noul", "instructions": "overclaim?"},
        },
        "expected": {"source_support": "fully_supported", "overclaim": False},
    },
    {
        "id": "unsupported",
        "suite": "answer_quality",
        "state": {"question": "q2", "sources": ["s2"], "draft_answer": "a2"},
        "questions": {},
        "expected": {},
    },
]


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def decide(self, request):
        self.requests.append(request)
        return next(self.responses)


def response(*, support="fully_supported", support_probability=0.8, overclaim=0.1):
    probabilities = {
        "fully_supported": support_probability if support == "fully_supported" else 0.1,
        "partially_supported": support_probability if support == "partially_supported" else 0.1,
        "unsupported": support_probability if support == "unsupported" else 0.1,
    }
    total = sum(probabilities.values())
    probabilities = {key: value / total for key, value in probabilities.items()}
    return {
        "model": "test-decider",
        "answers": {
            "source_support": {
                "type": "choice", "choice": support,
                "probabilities": probabilities, "confidence": 0.7,
            },
            "overclaim": {"type": "noul", "noul": overclaim},
        },
        "usage": {"input_tokens": 20, "output_tokens": 2},
        "latency_ms": 12.5,
    }


def test_build_request_never_sends_gold_labels():
    case = CASES[0]
    request = build_request(case, model="pinned-model")
    serialized = json.dumps(request)
    assert request["state"] == case["state"]
    assert request["questions"] == case["questions"]
    assert request["model"] == "pinned-model"
    assert "expected" not in serialized
    assert "fully_supported\", \"overclaim\": false" not in serialized.lower()


def test_evaluator_scores_choice_and_noul_without_emitting_content():
    case = CASES[0]
    report = evaluate_cases(
        FakeClient([response()]), [case], model="pinned-model", confidence_threshold=0.75
    )

    assert report["measurement"] == "decision_classification_not_legal_correctness"
    assert report["passed"] == 2
    assert report["total"] == 2
    assert report["accuracy"] == 1.0
    assert report["by_question"]["source_support"]["accuracy"] == 1.0
    assert report["by_question"]["overclaim"]["accuracy"] == 1.0
    assert report["by_suite"]["answer_quality"]["accuracy"] == 1.0
    assert report["by_jurisdiction"]["SE"]["accuracy"] == 1.0
    assert report["high_confidence"]["total"] == 1
    assert report["high_confidence"]["accuracy"] == 1.0
    assert report["high_confidence"]["coverage"] == 0.5
    assert report["cases"][0]["predictions"] == {
        "source_support": "fully_supported", "overclaim": False,
    }
    serialized = json.dumps(report)
    assert '"question": "q"' not in serialized
    assert '"draft_answer": "a"' not in serialized
    assert '"sources": ["s"]' not in serialized


def test_evaluator_reports_failures_and_brier_score():
    case = CASES[0]
    report = evaluate_cases(
        FakeClient([response(support="unsupported", support_probability=0.8, overclaim=0.9)]),
        [case],
    )
    assert report["passed"] == 0
    assert report["accuracy"] == 0.0
    assert report["brier_score"] > 0.5
    assert report["cases"][0]["passed"] is False


@pytest.mark.parametrize("threshold", [-0.1, 1.1])
def test_confidence_threshold_must_be_probability(threshold):
    with pytest.raises(ValueError):
        evaluate_cases(FakeClient([]), [CASES[0]], confidence_threshold=threshold)


@pytest.mark.parametrize("bad_response", [
    {},
    {"answers": {}},
    {"answers": {"source_support": {"type": "choice", "choice": "invented",
                                      "probabilities": {"invented": 1.0}, "confidence": 1.0},
                 "overclaim": {"type": "noul", "noul": 0.1}}},
    {"answers": {"source_support": {"type": "choice", "choice": "fully_supported",
                                      "probabilities": {"fully_supported": 1.0}, "confidence": 1.0},
                 "overclaim": {"type": "noul", "noul": 3.0}}},
    {"answers": {"source_support": {"type": "choice", "choice": "fully_supported",
                                      "probabilities": {"fully_supported": 0.8,
                                                        "partially_supported": 0.1,
                                                        "unsupported": 0.1}, "confidence": 2.0},
                 "overclaim": {"type": "noul", "noul": 0.1}}},
])
def test_malformed_model_responses_fail_closed(bad_response):
    with pytest.raises(ValueError):
        evaluate_cases(FakeClient([bad_response]), [CASES[0]])


def test_http_client_rejects_remote_endpoint_by_default():
    with pytest.raises(ValueError, match="loopback"):
        DeciderHTTPClient("https://decider.example.test")


def test_benchmark_dataset_has_routing_and_answer_cases_without_secrets():
    from src.benchmarks.decider_quality_data import (
        ANSWER_QUESTIONS,
        DECIDER_QUALITY_CASES,
        ROUTING_QUESTIONS,
    )

    suites = {case["suite"] for case in DECIDER_QUALITY_CASES}
    assert suites == {"routing", "answer_quality"}
    assert len(DECIDER_QUALITY_CASES) >= 12
    assert len({case["id"] for case in DECIDER_QUALITY_CASES}) == len(DECIDER_QUALITY_CASES)
    serialized = json.dumps(DECIDER_QUALITY_CASES).lower()
    assert "api_key" not in serialized
    assert "personnummer" not in serialized
    assert "claims_grounded" in ANSWER_QUESTIONS
    assert "overclaim" not in ANSWER_QUESTIONS
    assert "language alone" in ROUTING_QUESTIONS["jurisdiction"]["instructions"].lower()
    for case in DECIDER_QUALITY_CASES:
        assert case["state"]
        assert case["questions"]
        assert set(case["expected"]) == set(case["questions"])


def test_routing_cases_tell_model_which_capabilities_are_available():
    from src.benchmarks.decider_quality_data import DECIDER_QUALITY_CASES

    routing = [case for case in DECIDER_QUALITY_CASES if case["suite"] == "routing"]
    for case in routing:
        context = case["state"]["available_capabilities"]
        assert "SE, DK, FI, NO, DE, ES, NL and GB" in context
        assert "Sweden only" in context
