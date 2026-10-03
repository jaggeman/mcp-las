from src.db.firebase_client import FirebaseLaborLawDB


OFFICIAL_CASE = {
    "id": "AD_2022_nr_12",
    "case_number": "AD 2022 nr 12",
    "year": 2022,
    "title": "AD 2022 nr 12",
    "summary": "Ett bolag är bundet av två konkurrerande kollektivavtal.",
    "source": "Arbetsdomstolen",
    "source_url": (
        "https://arbetsdomstolen.se/sv/meddelade-domar/arkiverade-domar/"
        "2022/2022-03-01-ad-2022-nr-12/"
    ),
    "verification_status": "official_verified",
    "active": True,
    "embedding": [1.0, 0.0],
}


def _database_with(rows):
    database = object.__new__(FirebaseLaborLawDB)
    database.db = None
    database._local_precedents = {row["id"]: dict(row) for row in rows}
    database._cached_precedents = None
    return database


def test_unverified_precedents_are_never_searchable(monkeypatch):
    fake = dict(OFFICIAL_CASE)
    fake.pop("verification_status")
    fake["summary"] = "Påhittad sammanfattning"
    database = _database_with([fake])
    monkeypatch.setattr("src.db.firebase_client.Embedder.get_embedding", lambda _text: [1.0, 0.0])

    assert database.search_precedents("AD 2022 nr 12") == []


def test_verified_precedent_returns_official_provenance(monkeypatch):
    database = _database_with([OFFICIAL_CASE])
    monkeypatch.setattr("src.db.firebase_client.Embedder.get_embedding", lambda _text: [1.0, 0.0])

    rows = database.search_precedents("AD 2022 nr 12")

    assert len(rows) == 1
    assert rows[0]["case_number"] == "AD 2022 nr 12"
    assert rows[0]["source"] == "Arbetsdomstolen"
    assert rows[0]["source_url"] == OFFICIAL_CASE["source_url"]
    assert rows[0]["verification_status"] == "official_verified"


def test_non_ad_domain_cannot_be_marked_verified(monkeypatch):
    fake = dict(OFFICIAL_CASE, source_url="https://example.com/ad-2022-12")
    database = _database_with([fake])
    monkeypatch.setattr("src.db.firebase_client.Embedder.get_embedding", lambda _text: [1.0, 0.0])

    assert database.search_precedents("AD 2022 nr 12") == []


def test_inactive_official_precedent_is_not_searchable(monkeypatch):
    database = _database_with([dict(OFFICIAL_CASE, active=False)])
    monkeypatch.setattr("src.db.firebase_client.Embedder.get_embedding", lambda _text: [1.0, 0.0])

    assert database.search_precedents("AD 2022 nr 12") == []


def test_save_precedent_rejects_unverified_data_before_local_cache():
    database = _database_with([])
    fake = dict(OFFICIAL_CASE)
    fake.pop("verification_status")

    assert database.save_precedent(fake) is False
    assert database._local_precedents == {}


def test_exact_ad_number_is_ranked_first(monkeypatch):
    other = dict(
        OFFICIAL_CASE,
        id="AD_2022_nr_34",
        case_number="AD 2022 nr 34",
        title="AD 2022 nr 34",
        source_url="https://arbetsdomstolen.se/sv/meddelade-domar/2022/ad-34/",
        summary="Ett annat kollektivavtalsmål.",
    )
    database = _database_with([other, OFFICIAL_CASE])
    monkeypatch.setattr("src.db.firebase_client.Embedder.get_embedding", lambda _text: [1.0, 0.0])

    rows = database.search_precedents("AD 2022 nr 12", limit=2)

    assert [row["case_number"] for row in rows] == ["AD 2022 nr 12", "AD 2022 nr 34"]
