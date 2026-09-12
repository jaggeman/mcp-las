"""Weekly synchronization entry point for official legal sources."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.sync_service import DEFAULT_STATUTES, SourceSyncService


if __name__ == "__main__":
    args = [arg for arg in sys.argv[1:] if arg != "--danish"]
    include_danish = "--danish" in sys.argv[1:] or not args
    statutes = args or list(DEFAULT_STATUTES)
    service = SourceSyncService()
    summary = service.sync_statutes(statutes)
    if include_danish:
        danish_summary = service.sync_danish_documents()
        summary["danish"] = danish_summary
        summary["changed"] += danish_summary["changed"]
        summary["skipped"] += danish_summary["skipped"]
        summary["errors"] += danish_summary["errors"]
        if danish_summary["status"] == "error":
            summary["status"] = "error"
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(1 if summary["status"] == "error" else 0)
