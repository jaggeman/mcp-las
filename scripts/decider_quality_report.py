"""Run the optional local Strands Decider shadow benchmark."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.benchmarks.decider_quality import DEFAULT_MODEL, DeciderHTTPClient, evaluate_cases
from src.benchmarks.decider_quality_data import DECIDER_QUALITY_CASES


def run(base_url="http://127.0.0.1:8000", model=DEFAULT_MODEL, timeout=120,
        allow_remote=False, confidence_threshold=0.9):
    client = DeciderHTTPClient(base_url, timeout=timeout, allow_remote=allow_remote)
    report = evaluate_cases(
        client, DECIDER_QUALITY_CASES, model=model,
        confidence_threshold=confidence_threshold,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate routing and source-support decisions; not legal correctness."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--confidence-threshold", type=float, default=0.9)
    parser.add_argument(
        "--allow-remote", action="store_true",
        help="Allow sending synthetic benchmark text to a non-loopback Decider server.",
    )
    args = parser.parse_args()
    run(args.base_url, args.model, args.timeout, args.allow_remote,
        args.confidence_threshold)
