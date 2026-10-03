from src.scrapers.arbetsdomstolen_fetcher import (
    build_verified_precedents,
    fetch_verified_precedents,
    parse_archive_page,
)


ARCHIVE_HTML = """
<html><body>
  <div class="small-12 columns">
    <div class="card"><div class="card-divider"><h3>
      <a href="/sv/meddelade-domar/arkiverade-domar/2022/case/">2022-03-01, AD 2022 nr 12</a>
    </h3></div></div>
    <p class="card-text-info toggle-area">Officiellt referat om kollektivavtal.</p>
  </div>
  <div class="small-12 columns">
    <div class="card"><div class="card-divider"><h3>
      <a href="/sv/meddelade-domar/arkiverade-domar/2022/hidden/">2022-03-08, AD 2022 nr 13</a>
    </h3></div></div>
    <p class="card-text-info toggle-area">Domen refereras inte</p>
  </div>
</body></html>
"""

LEGACY_ARCHIVE_HTML = """
<html><body><div class="small-12 columns">
  <div class="card"><div class="card-divider"><h3>
    <a href="/sv/meddelade-domar/arkiverade-domar/2008/2008-12-17-dom-nr-11008/">
      2008-12-17 - Dom nr 110/08, Mål nr A 207/07, 2008-12-17
    </a>
  </h3></div></div>
  <p class="card-text-info toggle-area">Föreningsrättskränkning m.m.</p>
</div></body></html>
"""


def test_build_verified_precedents_uses_only_official_referats():
    parsed = parse_archive_page(ARCHIVE_HTML, 2022)

    rows = build_verified_precedents(parsed.values(), verified_at="2026-10-03")

    assert rows == [{
        "id": "AD_2022_nr_12",
        "case_number": "AD 2022 nr 12",
        "year": 2022,
        "title": "AD 2022 nr 12",
        "summary": "Officiellt referat om kollektivavtal.",
        "source": "Arbetsdomstolen",
        "source_url": "https://arbetsdomstolen.se/sv/meddelade-domar/arkiverade-domar/2022/case/",
        "verification_status": "official_verified",
        "verified_at": "2026-10-03",
        "active": True,
    }]
    assert "domskal" not in rows[0]
    assert "parties" not in rows[0]
    assert "slut" not in rows[0]


def test_parse_archive_page_supports_legacy_dom_number_headings():
    parsed = parse_archive_page(LEGACY_ARCHIVE_HTML, 2008)

    assert parsed["AD 2008 nr 110"]["official_summary"] == "Föreningsrättskränkning m.m."


class _Response:
    encoding = None

    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(response=self)


class _Session:
    def get(self, url, **_kwargs):
        return _Response(404 if "/2023/" in url else 200, ARCHIVE_HTML)


def test_fetch_verified_precedents_skips_years_without_an_archive():
    rows = fetch_verified_precedents(
        start_year=2022,
        end_year=2023,
        session=_Session(),
    )

    assert [row["case_number"] for row in rows] == ["AD 2022 nr 12"]


def test_fetch_verified_precedents_does_not_hide_a_missing_historical_archive():
    import pytest
    import requests

    with pytest.raises(requests.HTTPError):
        fetch_verified_precedents(
            start_year=2023,
            end_year=2024,
            session=_Session(),
        )
