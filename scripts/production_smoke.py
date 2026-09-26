"""Post-deploy checks through the public Firebase domain and MCP transport."""

import argparse
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.benchmarks.search_quality_data import SEARCH_QUALITY_CASES

SMOKE_QUERIES = {
    "SE": "provanställning",
    "DK": "ferie",
    "FI": "työsopimus",
    "NO": "arbeidsmiljø",
    "DE": "Kündigung",
    "ES": "vacaciones",
    "NL": "arbeidsovereenkomst",
    "GB": "unfair dismissal",
}


def parse_sse_json(body: str) -> dict:
    data_lines = []
    collecting = False
    for line in body.replace("\r\n", "\n").split("\n"):
        if line.startswith("data:"):
            collecting = True
            data_lines.append(line[5:].lstrip())
        elif collecting and line and not line.startswith(("event:", "id:", "retry:")):
            data_lines.append(line)
        elif collecting and not line:
            break
    if data_lines:
        return json.loads("\n".join(data_lines))
    raise ValueError("MCP response did not contain an SSE data event")


class MCPClient:
    def __init__(self, base_url: str):
        self.url = base_url.rstrip("/") + "/mcp"
        self.session = requests.Session()
        self.session_id = None
        self.next_id = 1

    def request(self, method: str, params: dict) -> dict:
        request_id = self.next_id
        self.next_id += 1
        headers = {"Accept": "application/json, text/event-stream"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        response = self.session.post(
            self.url,
            headers=headers,
            json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
            timeout=30,
        )
        response.raise_for_status()
        response.encoding = "utf-8"
        if not self.session_id:
            self.session_id = response.headers.get("Mcp-Session-Id")
        payload = parse_sse_json(response.text)
        if payload.get("error"):
            raise RuntimeError(f"MCP {method} failed")
        return payload["result"]

    def initialize(self):
        return self.request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "mcp-las-production-smoke", "version": "1.0"},
        })


def _assert_fast(response, maximum: float, label: str):
    if response.elapsed.total_seconds() > maximum:
        raise RuntimeError(f"{label} exceeded the response-time threshold")


def _matches_expected(result: dict, expected: list) -> bool:
    normalize = lambda value: str(value or "").lower().replace(" ", "")
    law = normalize(result.get("statute"))
    chapter = normalize(result.get("chapter"))
    section = normalize(result.get("section"))
    return any(
        normalize(wanted_law) in law
        and (wanted_chapter is None or normalize(wanted_chapter) == chapter)
        and normalize(wanted_section) == section
        for wanted_law, wanted_chapter, wanted_section in expected
    )


def run(base_url: str, expected_sha: str | None = None, max_response_seconds: float = 10,
        check_search_quality: bool = False):
    base_url = base_url.rstrip("/")
    health = requests.get(f"{base_url}/health", timeout=20)
    health.raise_for_status()
    _assert_fast(health, max_response_seconds, "health")
    health_data = health.json()
    if expected_sha and health_data.get("build_sha") != expected_sha:
        raise RuntimeError("production build SHA does not match the deployed commit")

    home = requests.get(f"{base_url}/", timeout=20)
    home.raise_for_status()
    _assert_fast(home, max_response_seconds, "landing page")
    if "data-coverage-desc" not in home.text:
        raise RuntimeError("landing page is missing live coverage placeholders")

    coverage_response = requests.get(f"{base_url}/api/coverage", timeout=20)
    coverage_response.raise_for_status()
    _assert_fast(coverage_response, max_response_seconds, "coverage API")
    coverage = coverage_response.json()["jurisdictions"]
    for country in ("SE", "NO", "DE", "ES"):
        if not coverage[country]["statutes"] or coverage[country]["section_count"] <= 0:
            raise RuntimeError(f"{country} unexpectedly has no indexed statutes")

    client = MCPClient(base_url)
    initialized = client.initialize()
    if initialized.get("serverInfo", {}).get("name") != "mcp-las" or not client.session_id:
        raise RuntimeError("MCP initialize did not return the expected server/session")
    tools = client.request("tools/list", {})
    names = {tool["name"] for tool in tools.get("tools", [])}
    if not {"get_legal_coverage", "lookup_statute", "search_labor_law"} <= names:
        raise RuntimeError("required MCP tools are missing")

    for country, status in coverage.items():
        if not status.get("statutes"):
            continue
        result = client.request("tools/call", {
            "name": "search_labor_law",
            "arguments": {"query": SMOKE_QUERIES[country], "jurisdiction": country, "limit": 1},
        })
        if result.get("isError") or not result.get("content"):
            raise RuntimeError(f"MCP search failed for {country}")

    if check_search_quality:
        failed = []
        for case in SEARCH_QUALITY_CASES:
            call = client.request("tools/call", {
                "name": "search_labor_law",
                "arguments": {"query": case["question"], "jurisdiction": "SE", "limit": 1},
            })
            rows = call.get("structuredContent", {}).get("result", [])
            if not rows or not _matches_expected(rows[0], case["expected"]):
                failed.append(case["id"])
        if failed:
            raise RuntimeError(f"search quality regression in {len(failed)} cases: {', '.join(failed)}")

    return {"health": health_data, "coverage": coverage, "tool_count": len(names),
            "search_quality_cases": len(SEARCH_QUALITY_CASES) if check_search_quality else 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://las.novro.se")
    parser.add_argument("--expected-sha")
    parser.add_argument("--max-response-seconds", type=float, default=10)
    parser.add_argument("--check-search-quality", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.base_url, args.expected_sha, args.max_response_seconds,
                         args.check_search_quality), ensure_ascii=False, indent=2))
