"""Pure retrieval metrics, not legal confidence scores."""
import re
from urllib.parse import urlparse


OFFICIAL_SOURCE_HOSTS = {
    "SE": ("riksdagen.se",),
    "DK": ("retsinformation.dk",),
    "FI": ("finlex.fi",),
    "NO": ("lovdata.no",),
    "DE": ("gesetze-im-internet.de",),
    "ES": ("boe.es",),
    "NL": ("wetten.overheid.nl",),
    "GB": ("legislation.gov.uk",),
}


def is_official_source_url(value, jurisdiction):
    """Require HTTPS and a known official legal-source host."""
    try:
        parsed = urlparse(str(value or ""))
        host = (parsed.hostname or "").casefold().rstrip(".")
    except ValueError:
        return False
    allowed = OFFICIAL_SOURCE_HOSTS.get(str(jurisdiction or "").upper(), ())
    return parsed.scheme == "https" and bool(parsed.path) and any(
        host == suffix or host.endswith("." + suffix) for suffix in allowed
    )


def normalize(value):
    return re.sub(r"\s+", "", str(value or "")).casefold()


def parse_reference(reference):
    match = re.fullmatch(r"(.+?)\s+(?:(\d+)\s+kap\.?\s+)?(\d+\s*[a-z]?)\s*§", reference.strip(), re.I)
    if not match:
        raise ValueError(f"Unsupported benchmark reference: {reference}")
    law, chapter, section = match.groups()
    return re.sub(r"^SFS\s+", "", law, flags=re.I), chapter, normalize(section)


def matches_reference(row, reference):
    law, chapter, section = reference
    identifiers = {normalize(row.get(key)) for key in ("statute", "law", "sfs_number")}
    return (bool(normalize(law)) and normalize(law) in identifiers
            and normalize(row.get("chapter")) == normalize(chapter)
            and normalize(row.get("section")) == normalize(section))


def evaluate_retrieval(rows, expected, jurisdiction):
    """Expected references are all required, not alternatives. No data retrieval."""
    if not expected:
        raise ValueError("At least one expected reference is required")
    expected = list(dict.fromkeys(tuple(ref) for ref in expected))
    def matches(row, ref):
        return (isinstance(row, dict) and row.get("jurisdiction") == jurisdiction
                and matches_reference(row, ref))
    ranks = [next((i for i, row in enumerate(rows, 1) if matches(row, ref)), None)
             for ref in expected]
    first = min((rank for rank in ranks if rank is not None), default=None)
    return {
        "hit_at_1": int(first == 1),
        "recall_at_5": sum(rank is not None and rank <= 5 for rank in ranks) / len(expected),
        "recall_at_10": sum(rank is not None and rank <= 10 for rank in ranks) / len(expected),
        "reciprocal_rank": 1 / first if first else 0.0,
        "jurisdiction_match": bool(rows) and all(isinstance(row, dict) and row.get("jurisdiction") == jurisdiction for row in rows),
        "official_sources": bool(rows) and all(
            isinstance(row, dict) and is_official_source_url(row.get("source_url"), jurisdiction)
            for row in rows
        ),
        "missing_references": [list(ref) for ref, rank in zip(expected, ranks) if rank is None],
        "measurement": "retrieval_only_not_legal_correctness",
    }
