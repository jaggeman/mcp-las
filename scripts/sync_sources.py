"""Weekly synchronization entry point for official legal sources."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.sync_service import DEFAULT_STATUTES, SourceSyncService


if __name__ == "__main__":
    raw_args = sys.argv[1:]
    source_flags = {"--swedish", "--danish", "--finnish", "--norwegian", "--german", "--spanish", "--dutch", "--british"}
    args = [arg for arg in raw_args if arg not in source_flags]
    explicit_sources = source_flags.intersection(raw_args)
    include_swedish = "--swedish" in raw_args or not explicit_sources
    include_danish = "--danish" in raw_args
    include_finnish = "--finnish" in raw_args
    statutes = args or list(DEFAULT_STATUTES)
    service = SourceSyncService()

    summary = {"changed": 0, "skipped": 0, "errors": 0, "items": [], "status": "success"}
    if include_swedish:
        swedish_summary = service.sync_statutes(statutes)
        summary.update({key: swedish_summary[key] for key in ("changed", "skipped", "errors", "items", "status")})
        summary['items'] = list(swedish_summary['items'])
        summary["swedish"] = swedish_summary

    if include_danish:
        danish_summary = service.sync_danish_documents()
        summary["danish"] = danish_summary
        summary["changed"] += danish_summary["changed"]
        summary["skipped"] += danish_summary["skipped"]
        summary["errors"] += danish_summary["errors"]
        summary["items"].extend(danish_summary["items"])
        if danish_summary["status"] == "error":
            summary["status"] = "error"
    if include_finnish:
        finnish_summary = service.sync_finnish_documents()
        summary["finnish"] = finnish_summary
        summary["changed"] += finnish_summary["changed"]
        summary["skipped"] += finnish_summary["skipped"]
        summary["errors"] += finnish_summary["errors"]
        summary["items"].extend(finnish_summary["items"])
        if finnish_summary["status"] == "error":
            summary["status"] = "error"
    if '--spanish' in raw_args:
        spanish_summary = service.sync_spanish_statutes()
        summary['ES'] = spanish_summary
        for key in ('changed', 'skipped', 'errors'):
            summary[key] += spanish_summary[key]
        summary['items'].extend(spanish_summary['items'])
        if spanish_summary['status'] == 'error': summary['status'] = 'error'
    for flag, country in (("--norwegian", "NO"), ("--german", "DE")):
        if flag in raw_args:
            country_summary = service.sync_european_statutes(country)
            summary[country] = country_summary
            for key in ('changed', 'skipped', 'errors'):
                summary[key] += country_summary[key]
            summary['items'].extend(country_summary['items'])
            if country_summary['status'] == 'error':
                summary['status'] = 'error'
    for flag, country in (("--dutch", "NL"), ("--british", "GB")):
        if flag in raw_args:
            country_summary = service.sync_official_statutes(country)
            summary[country] = country_summary
            for key in ('changed', 'skipped', 'errors'):
                summary[key] += country_summary[key]
            summary['items'].extend(country_summary['items'])
            if country_summary['status'] == 'error':
                summary['status'] = 'error'
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(1 if summary["status"] == "error" else 0)
