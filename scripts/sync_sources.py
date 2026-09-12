"""Weekly synchronization entry point for official legal sources."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.sync_service import DEFAULT_STATUTES, SourceSyncService


if __name__ == "__main__":
    statutes = sys.argv[1:] or list(DEFAULT_STATUTES)
    summary = SourceSyncService().sync_statutes(statutes)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(1 if summary["status"] == "error" else 0)
