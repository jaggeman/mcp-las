"""Read-only usage report: python -m scripts.usage_report --days 7."""
import argparse
import json
import math
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days', type=int, default=7, choices=range(1, 31), metavar='1-30')
    args = parser.parse_args()
    from google.cloud.firestore_v1.base_query import FieldFilter
    from src.db.firebase_client import db_client
    if db_client.db is None:
        parser.exit(1, 'Firestore is not configured; usage report unavailable.\n')
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    # Bound reads and clearly mark incomplete results instead of presenting
    # a truncated count as total usage. No public statistics endpoint.
    docs = list(db_client.db.collection('access_logs')
                .where(filter=FieldFilter('timestamp', '>=', start.isoformat()))
                .where(filter=FieldFilter('timestamp', '<=', end.isoformat()))
                .order_by('timestamp').limit(10001).stream())
    report = summarize(doc.to_dict() for doc in docs[:10000])
    report.update({'from_utc': start.isoformat(), 'to_utc': end.isoformat(),
                   'truncated': len(docs) > 10000,
                   'source': 'Firestore access_logs; failed log writes are not included'})
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
