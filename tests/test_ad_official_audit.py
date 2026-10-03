from src.benchmarks.ad_official_audit import (
    audit_local_cases,
    classify_verifiable_cases,
    fetch_and_audit,
    parse_archive_page,
)


ARCHIVE_HTML = """
<html><body>
  <div class="small-12 columns">
    <div class="card no-shadow clickableArea highlight">
      <div class="card-divider"><h3><a href="/sv/dom/2022-03-01-ad-2022-nr-12/">
        2022-03-01, AD 2022 nr 12
      </a></h3></div>
    </div>
    <p class="card-text-info toggle-area">
      Ett bolag är bundet av två konkurrerande kollektivavtal.
    </p>
  </div>
  <div class="small-12 columns">
    <div class="card"><div class="card-divider"><h3>
      <a href="/sv/dom/2022-03-08-ad-2022-nr-13/">2022-03-08, AD 2022 nr 13</a>
    </h3></div></div>
    <p class="card-text-info toggle-area">Domen refereras inte</p>
  </div>
</body></html>
"""


def test_parse_archive_page_extracts_official_summary_and_url():
    cases = parse_archive_page(ARCHIVE_HTML, 2022)

    assert cases["AD 2022 nr 12"] == {
        "case_number": "AD 2022 nr 12",
        "year": 2022,
        "status": "official_summary",
        "official_summary": "Ett bolag är bundet av två konkurrerande kollektivavtal.",
        "source_url": "https://arbetsdomstolen.se/sv/dom/2022-03-01-ad-2022-nr-12/",
    }


def test_parse_archive_page_marks_unreported_decisions():
    cases = parse_archive_page(ARCHIVE_HTML, 2022)

    assert cases["AD 2022 nr 13"]["status"] == "unreported"
    assert cases["AD 2022 nr 13"]["official_summary"] is None


def test_audit_local_cases_separates_verifiable_unreported_and_missing():
    official = parse_archive_page(ARCHIVE_HTML, 2022)
    local = [
        {"case_number": "AD 2022 nr 12", "title": "Fel ämne"},
        {"case_number": "AD 2022 nr 13", "title": "Kan inte verifieras publikt"},
        {"case_number": "AD 2022 nr 99", "title": "Saknas"},
    ]

    report = audit_local_cases(local, official)

    assert report["counts"] == {
        "total": 3,
        "official_summary": 1,
        "unreported": 1,
        "missing": 1,
        "archive_unavailable": 0,
    }
    assert [row["status"] for row in report["cases"]] == [
        "official_summary",
        "unreported",
        "missing",
    ]
    assert report["cases"][0]["local_case"]["title"] == "Fel ämne"


class _Response:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text
        self.encoding = None

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(response=self)


class _Session:
    def get(self, url, **_kwargs):
        if "/1994/" in url:
            return _Response(404)
        return _Response(200, ARCHIVE_HTML)


def test_fetch_and_audit_distinguishes_an_unavailable_archive_year():
    local = [
        {"case_number": "AD 1994 nr 1", "year": 1994},
        {"case_number": "AD 2022 nr 12", "year": 2022},
    ]

    report = fetch_and_audit(local, session=_Session())

    assert report["counts"]["archive_unavailable"] == 1
    assert report["cases"][0]["status"] == "archive_unavailable"
    assert report["unavailable_years"] == [1994]


class _Decider:
    def decide(self, request):
        assert "expected" not in request["state"]
        assert request["state"]["official_source_excerpt"].startswith("Ett bolag")
        return {
            "answers": {
                "jurisdiction_consistent": {"type": "noul", "noul": 0.9},
                "source_support": {
                    "type": "choice",
                    "choice": "unsupported",
                    "confidence": 0.8,
                    "probabilities": {
                        "fully_supported": 0.1,
                        "partially_supported": 0.1,
                        "unsupported": 0.8,
                    },
                },
                "claims_grounded": {"type": "noul", "noul": 0.2},
            },
            "latency_ms": 12,
        }


def test_classify_verifiable_cases_uses_official_text_without_gold_labels():
    report = audit_local_cases(
        [{"case_number": "AD 2022 nr 12", "title": "Illojal konkurrens", "summary": "Fel"}],
        parse_archive_page(ARCHIVE_HTML, 2022),
    )

    result = classify_verifiable_cases(report, _Decider())

    assert result["counts"] == {
        "audited": 1,
        "fully_supported": 0,
        "partially_supported": 0,
        "unsupported": 1,
    }
    assert result["cases"][0]["claims_grounded"] is False
    assert "official_source_excerpt" not in result["cases"][0]
    assert "local_draft" not in result["cases"][0]
