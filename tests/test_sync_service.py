from types import SimpleNamespace

from src.services.sync_service import SourceSyncService, content_hash


class FakeDB:
    def __init__(self):
        self.states = {}
        self.statutes = []
        self.sections = []

    def get_sync_state(self, source_id):
        return self.states.get(source_id)

    def save_sync_state(self, source_id, state):
        self.states[source_id] = state

    def save_statute(self, metadata):
        self.statutes.append(metadata)

    def save_statute_section(self, section):
        self.sections.append(section)


class FakeFetcher:
    calls = 0

    @classmethod
    def get_statute(cls, sfs):
        cls.calls += 1
        metadata = SimpleNamespace(
            id=sfs,
            sfs_number=sfs,
            title="Testlag",
            short_name="TEST",
            document_url="https://example.test/lag",
            total_sections=1,
            model_dump=lambda: {"id": sfs, "sfs_number": sfs, "title": "Testlag"},
        )
        section = SimpleNamespace(
            id=f"{sfs}_s1",
            raw_text="1 § Testinnehåll",
            model_dump=lambda: {"id": f"{sfs}_s1", "raw_text": "1 § Testinnehåll"},
        )
        return metadata, [section]


def test_content_hash_is_stable_and_changes_with_content():
    assert content_hash("abc") == content_hash("abc")
    assert content_hash("abc") != content_hash("abd")


def test_sync_indexes_changed_statute_and_is_idempotent():
    db = FakeDB()
    service = SourceSyncService(db=db, fetcher=FakeFetcher)

    first = service.sync_statutes(["1982:80"])
    second = service.sync_statutes(["1982:80"])

    assert first["changed"] == 1
    assert first["skipped"] == 0
    assert second["changed"] == 0
    assert second["skipped"] == 1
    assert len(db.statutes) == 1
    assert len(db.sections) == 1
    assert db.states["statute:1982:80"]["status"] == "success"


def test_sync_records_error_and_continues_with_other_sources():
    class PartlyFailingFetcher(FakeFetcher):
        @classmethod
        def get_statute(cls, sfs):
            if sfs == "bad":
                raise RuntimeError("source unavailable")
            return super().get_statute(sfs)

    db = FakeDB()
    service = SourceSyncService(db=db, fetcher=PartlyFailingFetcher)

    result = service.sync_statutes(["bad", "1982:80"])

    assert result["changed"] == 1
    assert result["errors"] == 1
    assert result["items"][0]["status"] == "error"
    assert result["items"][1]["status"] == "changed"


def test_sync_indexes_changed_danish_document_with_jurisdiction():
    class DanishFetcher:
        @classmethod
        def get_changed_laws(cls):
            return [{"documentId": "A202400001", "href": "https://example.test/doc.xml"}]

        @classmethod
        def get_document(cls, document):
            metadata = {
                "id": "DK:A202400001",
                "title": "Funktionærlov",
                "source_url": document["href"],
                "jurisdiction": "DK",
                "language": "da",
            }
            section = SimpleNamespace(
                raw_text="§ 1. Loven gælder for funktionærer.",
                model_dump=lambda: {
                    "id": "dk-a202400001_s1",
                    "raw_text": "§ 1. Loven gælder for funktionærer.",
                    "jurisdiction": "DK",
                    "language": "da",
                },
            )
            return metadata, [section]

    db = FakeDB()
    service = SourceSyncService(db=db, danish_fetcher=DanishFetcher)

    result = service.sync_danish_documents()

    assert result["changed"] == 1
    assert db.statutes[0]["jurisdiction"] == "DK"
    assert db.sections[0]["language"] == "da"
