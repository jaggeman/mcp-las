"""Read-only usage report: python -m scripts.usage_report --days 7."""
import argparse
import json
import math
import os
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone


def summarize(records):
    rows = list(records)
    events = [r for r in rows if r.get('event') == 'las_tool_usage']
    result = {'total_calls': len(events), 'legacy_rows_excluded': len(rows) - len(events)}
    for field, label in [('tool_called', 'tool'), ('transport', 'transport'),
                         ('jurisdiction', 'country'), ('status', 'status')]:
        result['by_' + label] = dict(Counter(r.get(field, 'unknown') for r in events).most_common())
    result['by_day'] = dict(sorted(Counter(r['timestamp'][:10] for r in events).items()))
    durations = sorted(float(r['duration_ms']) for r in events)
    result['latency_ms'] = {
        'average': round(sum(durations) / len(durations), 2) if durations else None,
        'p95': durations[math.ceil(len(durations) * .95) - 1] if durations else None,
    }
    return result


def read_cloud_events(project, start, end, limit=10001):
    """Read the primary, structured usage events without a duplicate database."""
    executable = shutil.which('gcloud.cmd' if os.name == 'nt' else 'gcloud')
    if not executable:
        raise FileNotFoundError('gcloud CLI was not found')
    log_filter = (
        'resource.type="cloud_run_revision" '
        'resource.labels.service_name="mcp-las" '
        'jsonPayload.event="las_tool_usage" '
        f'timestamp>="{start.isoformat()}" timestamp<="{end.isoformat()}"'
    )
    completed = subprocess.run([
        executable, 'logging', 'read', log_filter,
        f'--project={project}', f'--limit={limit}', '--order=asc', '--format=json',
    ], check=True, capture_output=True, text=True)
    entries = json.loads(completed.stdout or '[]')
    return [entry.get('jsonPayload', {}) for entry in entries]


def read_firestore_events(start, end, limit=10001):
    from google.cloud.firestore_v1.base_query import FieldFilter
    from src.db.firebase_client import db_client
    if db_client.db is None:
        raise RuntimeError('Firestore is not configured')
    docs = list(db_client.db.collection('access_logs')
                .where(filter=FieldFilter('timestamp', '>=', start.isoformat()))
                .where(filter=FieldFilter('timestamp', '<=', end.isoformat()))
                .order_by('timestamp').limit(limit).stream())
    return [doc.to_dict() for doc in docs]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days', type=int, default=7, choices=range(1, 31), metavar='1-30')
    parser.add_argument('--source', choices=('cloud', 'firestore'), default='cloud')
    parser.add_argument('--project', default='paygap-prod')
    args = parser.parse_args()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    try:
        rows = (read_cloud_events(args.project, start, end) if args.source == 'cloud'
                else read_firestore_events(start, end))
    except (RuntimeError, subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as exc:
        parser.exit(1, f'Usage report unavailable: {exc}\n')
    # Bound reads and clearly mark incomplete results instead of presenting a
    # truncated count as total usage. No public statistics endpoint.
    report = summarize(rows[:10000])
    report.update({'from_utc': start.isoformat(), 'to_utc': end.isoformat(),
                   'truncated': len(rows) > 10000,
                   'source': ('Cloud Logging' if args.source == 'cloud'
                              else 'Firestore access_logs; failed log writes are not included')})
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
