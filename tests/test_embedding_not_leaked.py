# -*- coding: utf-8 -*-
"""compare_statute_vs_cba läcker rå embedding-data i svaret.

`db_client.get_cba_exception`/`compare_statute_vs_cba` (src/db/firebase_client.py)
returnerar de lagrade dokumenten rakt av — `agreement_rules`-poster via
`ingest_cba.py` och lagparagrafer via `get_statute_section` sparas båda med
en `embedding`-nyckel (en lista med ~500-1500 flyttal). `lookup_statute` och
`get_cba_exception` i src/mcp_tools/tools.py bygger egna vitlistade
svarsdictar och läcker därför inte detta — men `compare_statute_vs_cba`
returnerar `db_client`-resultatet oförändrat, embedding och allt, i både
`cba_rules` och `statute_baseline`.

En anropare har ingen användning för embeddingen, och för ett verkligt svar
(1536-dimensionell OpenAI-vektor, inte mock-vektorn i det här testet) blir
svaret flera tiotusentals tecken nästan enbart embeddings — precis det
sidofynd som noterades i issue #5 men aldrig åtgärdades.
"""
import pytest
from src.db.firebase_client import db_client
from src.mcp_tools.tools import compare_statute_vs_cba


def _contains_embedding_key(value) -> bool:
    if isinstance(value, dict):
        if "embedding" in value:
            return True
        return any(_contains_embedding_key(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_embedding_key(v) for v in value)
    return False


@pytest.fixture
def isolated_db(monkeypatch):
    old_sections, old_rules = db_client._local_sections, db_client._local_rules
    monkeypatch.setattr(db_client, "db", None)
    db_client._local_sections = {}
    db_client._local_rules = {}
    db_client._cached_statute_sections_by_country = {}
    yield
    db_client._local_sections, db_client._local_rules = old_sections, old_rules
    db_client._cached_statute_sections = None
    db_client._cached_statute_sections_by_country = {}
    db_client._search_indexes = {}


def test_compare_statute_vs_cba_does_not_leak_embeddings(isolated_db):
    db_client.save_statute_section({
        "id": "1982_80_s99_embedding_test",
        "statute_id": "1982:80",
        "statute_short": "LAS",
        "chapter": None,
        "section_number": "99",
        "section_title": "Testparagraf",
        "content": "Testinnehåll för embedding-läckagetest.",
        "keywords": ["test"],
        "embedding": [0.1, 0.2, 0.3],
    })
    db_client.save_cba_rule({
        "id": "test_avtal_embedding_leak",
        "agreement_name": "Testavtalet",
        "statute": "LAS",
        "section": "99",
        "topic": "Embedding-läckagetest",
        "rule_content": "Testregel för embedding-läckagetest.",
        "statutory_deviation_ref": "Test",
        "embedding": [0.4, 0.5, 0.6],
    })

    res = compare_statute_vs_cba(topic="Embedding-läckagetest", agreement_name="Testavtalet")

    assert res["cba_rules"], "testfixturen matchade inte - inget att kontrollera"
    assert not _contains_embedding_key(res), (
        f"compare_statute_vs_cba läcker rå embedding-data: {res!r}"
    )
