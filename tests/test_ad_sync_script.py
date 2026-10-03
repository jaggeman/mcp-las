from scripts.ingest_ad_cases import run


CASE = {
    "id": "AD_2022_nr_12",
    "case_number": "AD 2022 nr 12",
    "year": 2022,
    "title": "AD 2022 nr 12",
    "summary": "Officiellt referat.",
    "source": "Arbetsdomstolen",
    "source_url": "https://arbetsdomstolen.se/sv/meddelade-domar/x/",
    "verification_status": "official_verified",
    "verified_at": "2026-10-03",
    "active": True,
}


class _Database:
    db = object()

    def __init__(self, existing):
        self.existing = existing
        self.saved = []

    def list_precedents_for_sync(self):
        return self.existing

    def save_precedent(self, row):
        self.saved.append(row)
        return True


def test_ad_sync_skips_unchanged_verified_case():
    database = _Database([dict(CASE, embedding=[0.2])])

    report = run(
        database=database,
        fetcher=lambda **_kwargs: [dict(CASE)],
        embedder=lambda _text: [0.2],
    )

    assert report == {"fetched": 1, "changed": 0, "skipped": 1}
    assert database.saved == []


def test_ad_sync_writes_changed_official_case_with_embedding():
    database = _Database([])

    report = run(
        database=database,
        fetcher=lambda **_kwargs: [dict(CASE)],
        embedder=lambda _text: [0.2],
    )

    assert report == {"fetched": 1, "changed": 1, "skipped": 0}
    assert database.saved[0]["embedding"] == [0.2]
