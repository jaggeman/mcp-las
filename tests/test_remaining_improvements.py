import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import server
from src.data.danish_labor_law_catalog import DANISH_LABOR_LAW_CATALOG
from src.data.finnish_labor_law_catalog import FINNISH_LABOR_LAW_CATALOG
from src.scrapers.finlex_fetcher import FinlexFetcher
from src.scrapers.retsinformation_fetcher import RetsinformationFetcher
from src.services.sync_service import SourceSyncService


def test_danish_catalog_discovery_uses_only_ministry_labor_law_links(monkeypatch):
    html = """
    <a href="https://www.retsinformation.dk/eli/lta/2024/152">Ferieloven</a>
    <a href="https://www.retsinformation.dk/eli/lta/2017/1002?id=1">Funktionærloven</a>
    <a href="https://www.retsinformation.dk/eli/lta/2026/999">Ikke i katalogen</a>
    """

    class Response:
        text = html
        encoding = "utf-8"

        def raise_for_status(self):
            return None

    monkeypatch.setattr("src.scrapers.retsinformation_fetcher.requests.get", lambda *a, **k: Response())

    rows = RetsinformationFetcher.catalog_documents()

    assert {row["catalog_name"] for row in rows} == {"Ferieloven", "Funktionærloven"}
    assert all(row["href"].endswith("/xml") for row in rows)
    assert all(row["statute_id"] for row in rows)


def test_finnish_catalog_discovery_is_exact_and_preserves_official_act_numbers():
    rows = FinlexFetcher.catalog_documents()

    assert len(rows) == len(FINNISH_LABOR_LAW_CATALOG)
    assert {row["statute_id"] for row in rows} == {
        row["act_number"] for row in FINNISH_LABOR_LAW_CATALOG
    }
    assert all(row["akn_uri"].endswith("/fin@") for row in rows)


def test_foreign_sync_defaults_to_bounded_catalog_not_change_feed():
    calls = []

    class Fetcher:
        @classmethod
        def catalog_documents(cls):
            calls.append("catalog")
            return [{"id": "law", "statute_id": "law"}]

        @classmethod
        def get_changed_laws(cls):
            raise AssertionError("the unbounded change feed must not be used")

        @classmethod
        def get_document(cls, document):
            section = SimpleNamespace(
                raw_text="1 § text",
                model_dump=lambda: {"id": "law-1", "statute_id": "law", "raw_text": "1 § text"},
            )
            return {"id": "DK:law", "statute_id": "law"}, [section]

    class DB:
        def get_sync_state(self, source_id): return None
        def save_sync_state(self, source_id, state): return True
        def publish_statute(self, *args): return True

    result = SourceSyncService(db=DB(), danish_fetcher=Fetcher).sync_danish_documents()

    assert result["status"] == "success"
    assert calls == ["catalog"]


@pytest.mark.asyncio
async def test_public_coverage_endpoint_is_read_only_and_cacheable(monkeypatch):
    monkeypatch.setattr(server, "_get_legal_coverage", lambda: {
        "jurisdictions": {"SE": {"statutes": True, "section_count": 477}}
    })

    response = await server.public_legal_coverage(SimpleNamespace(method="GET"))
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload["jurisdictions"]["SE"]["section_count"] == 477
    assert response.headers["cache-control"] == "public, max-age=60"


def test_legal_coverage_exposes_last_country_sync_without_claiming_availability(monkeypatch):
    from src.mcp_tools import tools

    monkeypatch.setattr(tools.db_client, "count_sections_by_jurisdiction", lambda: {"DK": 12})
    monkeypatch.setattr(tools.db_client, "get_sync_status_by_jurisdiction", lambda: {
        "DK": {"status": "success", "synced_at": "2026-09-26T10:00:00+00:00"}
    })

    dk = tools.get_legal_coverage()["jurisdictions"]["DK"]
    assert dk["section_count"] == 12
    assert dk["sync_status"] == "success"
    assert dk["last_synced_at"] == "2026-09-26T10:00:00+00:00"


def test_website_loads_live_coverage_for_country_cards():
    html = Path("public/index.html").read_text(encoding="utf-8")

    assert "/api/coverage" in html
    assert "data-coverage-desc" in html
    assert "section_count" in html


def test_weekly_sync_and_deploy_image_include_danish_and_finnish_catalogs():
    sync = Path(".github/workflows/sync-sources.yml").read_text(encoding="utf-8")
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    for flag in ("--danish", "--finnish"):
        assert flag in ci
    assert "alla sex lagkataloger" in sync


def test_search_quality_benchmark_has_at_least_22_ground_truth_questions():
    from src.benchmarks.search_quality_data import SEARCH_QUALITY_CASES

    assert len(SEARCH_QUALITY_CASES) >= 22
    assert all(case["question"] and case["expected"] for case in SEARCH_QUALITY_CASES)
    assert len({case["id"] for case in SEARCH_QUALITY_CASES}) == len(SEARCH_QUALITY_CASES)


def test_production_smoke_sse_parser_extracts_jsonrpc_result():
    from scripts.production_smoke import parse_sse_json

    payload = parse_sse_json('event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n\n')
    assert payload["result"] == {"ok": True}


def test_scheduled_monitor_runs_the_full_public_smoke_test():
    workflow = Path(".github/workflows/monitor-prod.yml").read_text(encoding="utf-8")
    assert "schedule:" in workflow
    assert "production_smoke.py" in workflow
    assert "--max-response-seconds" in workflow
