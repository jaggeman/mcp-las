import pytest
from unittest.mock import patch, MagicMock
from src.services.riksdagen_api_service import riksdagen_api_service, RiksdagenAPIService
from src.mcp_tools.tools import search_parliament_and_legislation, get_parliament_document_details

def test_search_parliament_documents_live_or_mock():
    # Test query
    res = riksdagen_api_service.search_documents(query="anställningsskydd", limit=3)
    assert "query" in res
    assert res["query"] == "anställningsskydd"
    assert "total_hits" in res
    assert "documents" in res
    assert isinstance(res["documents"], list)
    if res["documents"]:
        doc = res["documents"][0]
        assert "id" in doc
        assert "title" in doc
        assert "doc_type_name" in doc
        assert "url_html" in doc

def test_search_parliament_empty_query():
    res = riksdagen_api_service.search_documents(query="", limit=5)
    assert res["total_hits"] == 0
    assert len(res["documents"]) == 0

def test_search_parliament_filtering_by_doc_type():
    res = riksdagen_api_service.search_documents(query="LAS", doc_types=["prop"], limit=2)
    assert "documents" in res
    assert isinstance(res["documents"], list)
    for doc in res["documents"]:
        assert doc["doc_type"] == "prop"

def test_get_document_details():
    # Test detail fetching on a known proposition e.g. HD03304
    res = riksdagen_api_service.get_document_details("HD03304")
    assert "dok_id" in res
    assert res["dok_id"].upper() == "HD03304"
    assert "title" in res
    assert "certainty" in res
    assert res["certainty"]["score_pct"] == 100

def test_mcp_tools_wrapper():
    # Test tool wrapper functions in src.mcp_tools.tools
    tool_res = search_parliament_and_legislation(query="turordning", doc_type="prop", limit=2)
    assert "query" in tool_res
    assert "documents" in tool_res
    assert "certainty" in tool_res

    detail_res = get_parliament_document_details(dok_id="HD03304")
    assert "dok_id" in detail_res
    assert "title" in detail_res

def test_caching_mechanism():
    service = RiksdagenAPIService()
    # Cache hit check
    mock_resp = {
        "dokumentlista": {
            "@traffar": "1",
            "dokument": [{
                "id": "test123",
                "dok_id": "TEST123",
                "titel": "Test Proposition",
                "doktyp": "prop",
                "rm": "2024/25",
                "beteckning": "100",
                "datum": "2024-01-01",
                "organ": "Arbetsmarknadsdepartementet",
                "dokument_url_html": "//data.riksdagen.se/dokument/TEST123.html",
                "notis": "Test notis"
            }]
        }
    }
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_resp)
        res1 = service.search_documents(query="mock_test_query", limit=1)
        assert res1["total_hits"] == 1
        assert res1["documents"][0]["id"] == "test123"
        assert mock_get.call_count == 1

        # Second call should use in-memory cache and not call httpx.get again
        res2 = service.search_documents(query="mock_test_query", limit=1)
        assert res2["total_hits"] == 1
        assert mock_get.call_count == 1
