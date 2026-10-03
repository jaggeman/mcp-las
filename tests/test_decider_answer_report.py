"""CLI report wiring for JSONL answer-quality shadow tests."""

import json


def test_report_adds_dataset_metadata_without_content(tmp_path, monkeypatch, capsys):
    from scripts import decider_answer_report as report_script

    row = {
        "id": "safe-1", "jurisdiction": "SE",
        "question": "PRIVATE QUESTION", "source_excerpts": ["PRIVATE SOURCE"],
        "draft_answer": "PRIVATE DRAFT",
        "expected": {
            "jurisdiction_consistent": True,
            "source_support": "fully_supported",
            "claims_grounded": True,
        },
        "review_status": "synthetic_unverified",
    }
    path = tmp_path / "cases.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def decide(self, _request):
            return {
                "model": "test",
                "answers": {
                    "jurisdiction_consistent": {"type": "noul", "noul": 0.9},
                    "source_support": {
                        "type": "choice", "choice": "fully_supported",
                        "probabilities": {
                            "fully_supported": 0.9,
                            "partially_supported": 0.05,
                            "unsupported": 0.05,
                        },
                        "confidence": 0.85,
                    },
                    "claims_grounded": {"type": "noul", "noul": 0.9},
                },
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "latency_ms": 1,
            }

    monkeypatch.setattr(report_script, "DeciderHTTPClient", Client)
    result = report_script.run(path)

    assert result["dataset"] == {
        "case_count": 1,
        "by_jurisdiction": {"SE": 1},
        "by_review_status": {"synthetic_unverified": 1},
    }
    assert result["release_gate"] == {
        "passed": 1, "total": 1, "accuracy": 1.0,
        "false_accepts": 0, "false_rejects": 0,
    }
    assert result["cases"][0]["predicted_disposition"] == "pass"
    assert result["cases"][0]["automated_action"] == "observe"
    output = capsys.readouterr().out
    assert "PRIVATE QUESTION" not in output
    assert "PRIVATE SOURCE" not in output
    assert "PRIVATE DRAFT" not in output
