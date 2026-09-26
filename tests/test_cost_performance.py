from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.config import settings
from src.db.auth_service import AuthService
from src.db.firebase_client import FirebaseLaborLawDB
from src.embeddings.embedder import Embedder
from src.services import usage_logging


def test_valid_key_cache_avoids_repeated_firestore_reads(monkeypatch):
    service = AuthService()
    reads=[]
    db=SimpleNamespace(collection=lambda _:SimpleNamespace(document=lambda digest:
        SimpleNamespace(get=lambda:(reads.append(1) or SimpleNamespace(
            id=digest, exists=True, to_dict=lambda:{'is_active':True,'name':'test','key_digest':digest})))))
    monkeypatch.setattr('src.db.auth_service.db_client.db',db)
    assert service.validate_key('valid-key')['name']=='test'
    assert service.validate_key('valid-key')['name']=='test'
    assert len(reads)==1
    assert 'valid-key' not in repr(service._key_cache)


def test_key_cache_expires_and_is_bounded(monkeypatch):
    service=AuthService(); clock=[100.0]; reads=[]
    db=SimpleNamespace(collection=lambda _:SimpleNamespace(document=lambda digest:
        SimpleNamespace(get=lambda:(reads.append(1) or SimpleNamespace(
            id=digest, exists=True, to_dict=lambda:{'is_active':True,'key_digest':digest})))))
    monkeypatch.setattr('src.db.auth_service.db_client.db',db)
    monkeypatch.setattr('src.db.auth_service.time.monotonic',lambda:clock[0])
    for n in range(1100): service.validate_key(f'key-{n}')
    assert len(service._key_cache)<=1000
    clock[0]+=31
    service.validate_key('key-1099')
    assert len(reads)==1101


def test_usage_firestore_copy_disabled_by_default(monkeypatch, capsys):
    put=Mock(); monkeypatch.setattr(usage_logging._pending,'put_nowait',put)
    monkeypatch.setattr(settings,'STORE_USAGE_IN_FIRESTORE',False)
    usage_logging.emit(tool='lookup_statute',transport='mcp',jurisdiction='SE',status='success',duration_ms=1)
    put.assert_not_called()
    assert 'las_tool_usage' in capsys.readouterr().out


def test_country_cache_reads_only_requested_jurisdiction(monkeypatch):
    db=FirebaseLaborLawDB.__new__(FirebaseLaborLawDB)
    db._local_sections={}; db._cached_statute_sections=None
    db._statute_cache_lock=__import__('threading').RLock()
    marker=SimpleNamespace(exists=True,to_dict=lambda:{'version':'v1'})
    query=SimpleNamespace(stream=lambda:[SimpleNamespace(to_dict=lambda:{'jurisdiction':'ES','active':True})])
    collection=SimpleNamespace(document=lambda _:SimpleNamespace(get=lambda:marker),where=lambda **_:query)
    db.db=SimpleNamespace(collection=lambda _:collection)
    rows=db._get_statute_items('ES')
    assert len(rows)==1 and rows[0]['jurisdiction']=='ES'


def test_country_and_search_caches_evict_old_corpora_to_bound_memory():
    import threading
    from collections import OrderedDict

    db = FirebaseLaborLawDB.__new__(FirebaseLaborLawDB)
    db.db = None
    db._statute_cache_lock = threading.RLock()
    db._cached_statute_sections_by_country = OrderedDict()
    db._country_cache_at = {}
    db._country_cache_version = {}
    db._country_full_read_at = {}
    db._search_indexes = OrderedDict()
    db._local_sections = {
        country: {"id": country, "jurisdiction": country, "content": "employment law", "active": True}
        for country in ("SE", "DK", "NL", "GB")
    }

    first_snapshot = None
    for country in ("SE", "DK", "NL", "GB"):
        snapshot = db._get_statute_items(country)
        first_snapshot = first_snapshot or snapshot
        db._search_index(snapshot, {"jurisdiction": country})

    assert list(db._cached_statute_sections_by_country) == ["DK", "NL", "GB"]
    assert all(entry[0] is not first_snapshot for entry in db._search_indexes.values())


def test_coverage_uses_aggregate_counts_not_full_corpus(monkeypatch):
    db=FirebaseLaborLawDB.__new__(FirebaseLaborLawDB); db.db=SimpleNamespace()
    monkeypatch.setattr(db,'_aggregate_country_count',lambda country:{'SE':537,'DE':405}.get(country,0))
    monkeypatch.setattr(db,'_get_statute_items',Mock(side_effect=AssertionError('full corpus read')))
    assert db.count_sections_by_jurisdiction()=={'SE':537,'DE':405}


def test_cloud_run_cost_caps_are_declared():
    workflow=open('.github/workflows/ci.yml',encoding='utf-8').read()
    assert '--max-instances=5' in workflow
    assert '--concurrency=40' in workflow
    server=open('src/server.py',encoding='utf-8').read()
    assert '"access_log": False' in server


def test_unchanged_version_marker_prevents_periodic_full_country_reads(monkeypatch):
    """A stable version marker makes the cached corpus authoritative.

    The marker is checked once a minute, but unchanged data must not be read in
    full again merely because five minutes have elapsed.
    """
    import threading
    from collections import OrderedDict

    clock = [100.0]
    reads = []
    marker = SimpleNamespace(exists=True, to_dict=lambda: {"version": "v1"})

    class Query:
        def stream(self):
            reads.append(1)
            return [SimpleNamespace(to_dict=lambda: {
                "id": "se-1", "jurisdiction": "SE", "active": True,
            })]

    class Collection:
        def document(self, _):
            return SimpleNamespace(get=lambda: marker)

        def where(self, **_):
            return Query()

    db = FirebaseLaborLawDB.__new__(FirebaseLaborLawDB)
    db.db = SimpleNamespace(collection=lambda _: Collection())
    db._local_sections = {}
    db._statute_cache_lock = threading.RLock()
    db._cached_statute_sections_by_country = OrderedDict()
    db._country_cache_at = {}
    db._country_cache_version = {}
    db._country_full_read_at = {}
    db._search_indexes = OrderedDict()
    monkeypatch.setattr("src.db.firebase_client.time.monotonic", lambda: clock[0])

    first = db._get_statute_items("SE")
    clock[0] += 301
    assert db._get_statute_items("SE") is first
    assert len(reads) == 1


def test_search_vectorizes_semantic_scoring(monkeypatch):
    """Semantic ranking must use one matrix operation, not one conversion per row."""
    import threading
    from collections import OrderedDict

    db = FirebaseLaborLawDB.__new__(FirebaseLaborLawDB)
    db.db = None
    db._statute_cache_lock = threading.RLock()
    db._cached_statute_sections_by_country = OrderedDict()
    db._country_cache_at = {}
    db._country_cache_version = {}
    db._country_full_read_at = {}
    db._search_indexes = OrderedDict()
    db._local_sections = {
        "a": {"id": "a", "jurisdiction": "SE", "content": "semester",
              "keywords": [], "embedding": [1.0, 0.0], "active": True},
        "b": {"id": "b", "jurisdiction": "SE", "content": "arbete",
              "keywords": [], "embedding": [0.0, 1.0], "active": True},
    }
    monkeypatch.setattr(Embedder, "get_embedding", classmethod(lambda cls, _: [1.0, 0.0]))
    monkeypatch.setattr(Embedder, "cosine_similarity",
                        lambda *_: (_ for _ in ()).throw(AssertionError("per-row cosine used")))

    rows = db.search_statute_sections("semester", {"jurisdiction": "SE"}, limit=2)

    assert rows[0]["content"] == "semester"
    index = next(iter(db._search_indexes.values()))
    assert index[4].dtype.name == "float32"


def test_compacted_local_embedding_can_be_saved_again(monkeypatch):
    """The float32 cache representation must remain valid for local updates."""
    import numpy as np

    db = FirebaseLaborLawDB.__new__(FirebaseLaborLawDB)
    db.db = None
    db._local_sections = {}
    db._statute_cache_lock = __import__("threading").RLock()
    db._cached_statute_sections = None
    db._cached_statute_sections_by_country = {}
    db._country_cache_at = {}
    db._search_indexes = {}
    row = {"id": "cached", "raw_text": "text", "embedding": np.ones(2, dtype=np.float32)}
    monkeypatch.setattr(Embedder, "get_embedding",
                        classmethod(lambda *_: (_ for _ in ()).throw(AssertionError("re-embedded"))))

    assert db.save_statute_section(row) is False


def test_riksdagen_cache_is_lru_bounded():
    from src.services.riksdagen_api_service import RiksdagenAPIService

    service = RiksdagenAPIService(cache_max_entries=2)
    service._set_cache("a", 1)
    service._set_cache("b", 2)
    assert service._get_from_cache("a") == 1  # a is now most recently used
    service._set_cache("c", 3)

    assert list(service._cache) == ["a", "c"]
    assert service._get_from_cache("b") is None


def test_hosting_only_rewrites_dynamic_routes():
    import json

    config = json.loads(open("firebase.json", encoding="utf-8").read())
    expected = {"/mcp", "/mcp/**", "/sse", "/sse/**", "/api", "/api/**", "/health"}
    for site in config["hosting"]:
        sources = {rule["source"] for rule in site["rewrites"]}
        assert sources == expected
        assert "**" not in sources


def test_ci_avoids_backend_deploy_for_static_only_changes():
    workflow = open(".github/workflows/ci.yml", encoding="utf-8").read()
    assert "backend_changed" in workflow
    assert "hosting_changed" in workflow
    assert "steps.changes.outputs.backend_changed == 'true'" in workflow


def test_artifact_registry_cleanup_policy_is_bounded():
    import json

    policies = json.loads(open(".github/artifact-cleanup-policy.json", encoding="utf-8").read())
    recent = next(p for p in policies if p["action"]["type"] == "Keep")
    delete = next(p for p in policies if p["action"]["type"] == "Delete")
    assert recent["mostRecentVersions"]["keepCount"] >= 10
    assert delete["condition"]["olderThan"] >= "14d"
