"""Fetch public case summaries from the Swedish Labour Court.

Only text that Arbetsdomstolen publishes as an official referat is converted
to a searchable precedent.  Unreported decisions are deliberately excluded.
"""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://arbetsdomstolen.se"
ARCHIVE_URL = BASE_URL + "/sv/meddelade-domar/arkiverade-domar/{year}/"
CASE_NUMBER_RE = re.compile(r"\bAD\s+(\d{4})\s+nr\s+(\d+)\b", re.IGNORECASE)
LEGACY_CASE_NUMBER_RE = re.compile(r"\b(?:dom|beslut)\s+nr\s+(\d+)\s*/\s*(\d{2})\b", re.IGNORECASE)
UNREPORTED_MARKERS = ("domen refereras inte", "beslutet refereras inte")


def normalize_case_number(value: str) -> str | None:
    match = CASE_NUMBER_RE.search(value or "")
    if not match:
        return None
    return f"AD {int(match.group(1))} nr {int(match.group(2))}"


def parse_archive_page(html: str, year: int) -> dict[str, dict]:
    soup = BeautifulSoup(html, "html.parser")
    cases = {}
    for heading in soup.find_all("h3"):
        link = heading.find("a", href=True)
        if not link:
            continue
        case_number = normalize_case_number(heading.get_text(" ", strip=True))
        if not case_number:
            legacy = LEGACY_CASE_NUMBER_RE.search(heading.get_text(" ", strip=True))
            if legacy and int(legacy.group(2)) == int(year) % 100:
                case_number = f"AD {int(year)} nr {int(legacy.group(1))}"
        if not case_number:
            continue
        container = heading.find_parent("div", class_="columns")
        summary_node = container.find("p", class_="card-text-info") if container else None
        summary = summary_node.get_text(" ", strip=True) if summary_node else ""
        is_unreported = any(marker in summary.casefold() for marker in UNREPORTED_MARKERS)
        cases[case_number] = {
            "case_number": case_number,
            "year": int(year),
            "status": "unreported" if is_unreported else "official_summary",
            "official_summary": None if is_unreported else summary or None,
            "source_url": urljoin(BASE_URL, link["href"]),
        }
    return cases


def fetch_archive_year(year: int, *, session=None, timeout: float = 30) -> dict[str, dict]:
    client = session or requests.Session()
    response = client.get(
        ARCHIVE_URL.format(year=int(year)),
        headers={"User-Agent": "MCP-LAS/1.0 (official-source-sync)"},
        timeout=timeout,
    )
    response.raise_for_status()
    response.encoding = "utf-8"
    return parse_archive_page(response.text, int(year))


def build_verified_precedents(cases, *, verified_at: str | None = None) -> list[dict]:
    verified_at = verified_at or date.today().isoformat()
    rows = []
    for case in cases:
        if case.get("status") != "official_summary" or not case.get("official_summary"):
            continue
        case_number = normalize_case_number(case.get("case_number", ""))
        if not case_number:
            continue
        rows.append({
            "id": case_number.replace(" ", "_"),
            "case_number": case_number,
            "year": int(case["year"]),
            "title": case_number,
            "summary": case["official_summary"],
            "source": "Arbetsdomstolen",
            "source_url": case["source_url"],
            "verification_status": "official_verified",
            "verified_at": verified_at,
            "active": True,
        })
    return sorted(rows, key=lambda row: (row["year"], row["case_number"]), reverse=True)


def fetch_verified_precedents(
    *, start_year: int = 2003, end_year: int | None = None,
    session=None, timeout: float = 30,
) -> list[dict]:
    end_year = end_year or date.today().year
    if start_year > end_year:
        raise ValueError("start_year must not be after end_year")
    cases = []
    for year in range(start_year, end_year + 1):
        try:
            archive = fetch_archive_year(year, session=session, timeout=timeout)
        except requests.HTTPError as exc:
            if (year == end_year and exc.response is not None
                    and exc.response.status_code == 404):
                continue
            raise
        cases.extend(archive.values())
    return build_verified_precedents(cases)
