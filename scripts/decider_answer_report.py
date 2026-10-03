"""Evaluate anonymised JSONL answer drafts with a local Strands Decider server."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.benchmarks.decider_answer_jsonl import load_answer_cases, summarize_cases
from src.benchmarks.decider_quality import DEFAULT_MODEL, DeciderHTTPClient, evaluate_cases


DEFAULT_INPUT = Path(__file__).parent.parent / "tests" / "data" / "decider_answer_cases.jsonl"


def run(input_path=DEFAULT_INPUT, base_url="http://127.0.0.1:8765",
        model=DEFAULT_MODEL, timeout=120, allow_remote=False,
        confidence_threshold=0.9):
    cases = load_answer_cases(input_path)
    client = DeciderHTTPClient(base_url, timeout=timeout, allow_remote=allow_remote)
    report = evaluate_cases(
        client, cases, model=model, confidence_threshold=confidence_threshold
    )
    report["dataset"] = summarize_cases(cases)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Shadow-evaluate already-anonymised answer drafts. Output excludes "
            "questions, source excerpts and draft answers."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--confidence-threshold", type=float, default=0.9)
    parser.add_argument(
        "--allow-remote", action="store_true",
        help="Allow sending the JSONL case content to a non-loopback Decider server.",
    )
    args = parser.parse_args()
    run(
        args.input, args.base_url, args.model, args.timeout,
        args.allow_remote, args.confidence_threshold,
    )
