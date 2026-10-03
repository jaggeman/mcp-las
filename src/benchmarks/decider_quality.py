"""Offline decision-model evaluation; never a legal-correctness score.

The production MCP server intentionally does not depend on Strands Decider.  This
module talks to a separately started System One HTTP server and keeps benchmark
gold labels out of the request sent to that server.
"""

from __future__ import annotations

import json
from collections import defaultdict
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_MODEL = "StrandsAgents/strands-decider-2B-hobson-v19"
MAX_RESPONSE_BYTES = 1024 * 1024


class DeciderHTTPClient:
    """Small dependency-free client for a local Strands System One server."""

    def __init__(self, base_url="http://127.0.0.1:8000", *, timeout=120, allow_remote=False):
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Decider URL must be an absolute HTTP(S) URL")
        if not allow_remote and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Decider URL must use a loopback host unless allow_remote=True")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def decide(self, request):
        body = json.dumps(request, ensure_ascii=False).encode("utf-8")
        http_request = Request(
            self.base_url + "/v1/systemone",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=self.timeout) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            detail = exc.read(4096).decode("utf-8", errors="replace")
            raise RuntimeError(f"Decider returned HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Could not reach Decider at {self.base_url}: {exc.reason}") from exc
        if len(payload) > MAX_RESPONSE_BYTES:
            raise ValueError("Decider response exceeds 1 MiB")
        try:
            value = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Decider returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("Decider response must be a JSON object")
        return value


def build_request(case, model=DEFAULT_MODEL):
    """Build model input without copying benchmark labels into the request."""
    return {
        "state": case["state"],
        "questions": case["questions"],
        "model": model,
    }


def _score_answer(answer, question, expected):
    if not isinstance(answer, dict) or answer.get("type") != question.get("type"):
        raise ValueError("Decider answer type does not match the requested question")
    if question["type"] == "noul":
        probability = answer.get("noul")
        if isinstance(probability, bool) or not isinstance(probability, (int, float)):
            raise ValueError("Noul answer must contain a numeric probability")
        probability = float(probability)
        if not 0 <= probability <= 1:
            raise ValueError("Noul probability must be between 0 and 1")
        prediction = probability >= 0.5
        expected_bool = bool(expected)
        return prediction, abs(2 * probability - 1), (probability - int(expected_bool)) ** 2

    if question["type"] != "choice":
        raise ValueError(f"Unsupported PoC question type: {question.get('type')}")
    options = set(question.get("criteria") or {})
    prediction = answer.get("choice")
    probabilities = answer.get("probabilities")
    if prediction not in options or not isinstance(probabilities, dict):
        raise ValueError("Choice answer is missing a valid prediction or probabilities")
    if set(probabilities) != options:
        raise ValueError("Choice probabilities do not match the requested options")
    try:
        numeric = {key: float(value) for key, value in probabilities.items()}
    except (TypeError, ValueError) as exc:
        raise ValueError("Choice probabilities must be numeric") from exc
    if any(value < 0 or value > 1 for value in numeric.values()) or not 0.99 <= sum(numeric.values()) <= 1.01:
        raise ValueError("Choice probabilities must form a probability distribution")
    if expected not in options:
        raise ValueError("Benchmark expected value is not a requested option")
    brier = sum((probability - int(option == expected)) ** 2
                for option, probability in numeric.items())
    confidence = answer.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("Choice answer must contain numeric confidence")
    confidence = float(confidence)
    if not 0 <= confidence <= 1:
        raise ValueError("Choice confidence must be between 0 and 1")
    return prediction, confidence, brier


def evaluate_cases(client, cases, *, model=DEFAULT_MODEL, confidence_threshold=0.9):
    """Evaluate typed decisions and return aggregate metrics without case content."""
    if not 0 <= confidence_threshold <= 1:
        raise ValueError("confidence_threshold must be between 0 and 1")
    case_rows = []
    measurements = []
    by_question = defaultdict(list)
    by_suite = defaultdict(list)
    by_jurisdiction = defaultdict(list)
    observed_models = set()
    release_gates = []
    total_input_tokens = 0
    total_latency_ms = 0.0

    for case in cases:
        response = client.decide(build_request(case, model=model))
        answers = response.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("Decider response is missing answers")
        if set(answers) != set(case["questions"]):
            raise ValueError("Decider response does not match requested question names")
        predictions = {}
        confidences = {}
        passed = True
        for name, question in case["questions"].items():
            prediction, confidence, brier = _score_answer(
                answers[name], question, case["expected"][name]
            )
            correct = prediction == case["expected"][name]
            passed = passed and correct
            predictions[name] = prediction
            confidences[name] = round(confidence, 6)
            measurement = {"correct": correct, "brier": brier, "confidence": confidence}
            measurements.append(measurement)
            by_question[name].append(measurement)
            by_suite[case["suite"]].append(measurement)
            jurisdiction = case.get("state", {}).get("requested_jurisdiction")
            if jurisdiction:
                by_jurisdiction[jurisdiction].append(measurement)

        usage = response.get("usage") or {}
        total_input_tokens += int(usage.get("input_tokens", 0) or 0)
        latency = float(response.get("latency_ms", 0) or 0)
        total_latency_ms += latency
        if response.get("model"):
            observed_models.add(str(response["model"]))
        case_row = {
            "id": case["id"],
            "suite": case["suite"],
            "passed": passed,
            "predictions": predictions,
            "confidences": confidences,
            "latency_ms": round(latency, 2),
        }
        gate_fields = {"jurisdiction_consistent", "source_support", "claims_grounded"}
        if gate_fields <= set(predictions):
            predicted_safe = (
                predictions["jurisdiction_consistent"] is True
                and predictions["source_support"] == "fully_supported"
                and predictions["claims_grounded"] is True
            )
            expected = case["expected"]
            expected_safe = (
                expected["jurisdiction_consistent"] is True
                and expected["source_support"] == "fully_supported"
                and expected["claims_grounded"] is True
            )
            gate_confidence = min(confidences[name] for name in gate_fields)
            disposition = "pass" if predicted_safe else "revise"
            case_row.update(
                predicted_disposition=disposition,
                automated_action=(
                    disposition if gate_confidence >= confidence_threshold else "observe"
                ),
                gate_confidence=round(gate_confidence, 6),
            )
            release_gates.append({
                "correct": predicted_safe == expected_safe,
                "false_accept": predicted_safe and not expected_safe,
                "false_reject": not predicted_safe and expected_safe,
            })
        case_rows.append(case_row)

    total = len(measurements)
    passed = sum(item["correct"] for item in measurements)

    def aggregate(rows, *, allow_empty=False):
        if not rows and allow_empty:
            return {"passed": 0, "total": 0, "accuracy": None, "brier_score": None}
        return {
            "passed": sum(item["correct"] for item in rows),
            "total": len(rows),
            "accuracy": round(sum(item["correct"] for item in rows) / len(rows), 6),
            "brier_score": round(sum(item["brier"] for item in rows) / len(rows), 6),
        }

    if not total:
        raise ValueError("At least one Decider benchmark decision is required")
    report = aggregate(measurements)
    high_confidence = [row for row in measurements
                       if row["confidence"] >= confidence_threshold]
    high_confidence_report = aggregate(high_confidence, allow_empty=True)
    high_confidence_report["coverage"] = round(len(high_confidence) / total, 6)
    release_gate_report = {
        "passed": sum(row["correct"] for row in release_gates),
        "total": len(release_gates),
        "accuracy": (round(sum(row["correct"] for row in release_gates)
                           / len(release_gates), 6) if release_gates else None),
        "false_accepts": sum(row["false_accept"] for row in release_gates),
        "false_rejects": sum(row["false_reject"] for row in release_gates),
    }
    report.update({
        "measurement": "decision_classification_not_legal_correctness",
        "requested_model": model,
        "observed_models": sorted(observed_models),
        "case_count": len(case_rows),
        "input_tokens": total_input_tokens,
        "average_latency_ms": round(total_latency_ms / len(case_rows), 2),
        "confidence_threshold": confidence_threshold,
        "high_confidence": high_confidence_report,
        "release_gate": release_gate_report,
        "by_question": {name: aggregate(rows) for name, rows in sorted(by_question.items())},
        "by_suite": {name: aggregate(rows) for name, rows in sorted(by_suite.items())},
        "by_jurisdiction": {
            name: aggregate(rows) for name, rows in sorted(by_jurisdiction.items())
        },
        "cases": case_rows,
    })
    return report
